import json
import asyncio
import logging
import uuid
import aio_pika
from enum import Enum
from src.core.events import events # Assuming this module contains base Event and specific event classes
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Tuple, Type
from src.service_layer.messagebus import MessageBus
from src.core.correlation.context import set_correlation_id
from src.adapters.message_broker.connection_manager import AbstractConnectionManager
from aio_pika.abc import AbstractRobustChannel, AbstractRobustQueue, AbstractIncomingMessage

logger = logging.getLogger(__name__)


class ProcessingResult(Enum):
    """Represents the result of processing a message."""
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"


class ExchangeType(Enum):
    """Enum representing supported RabbitMQ exchange types."""
    DIRECT = "direct"
    FANOUT = "fanout"
    TOPIC = "topic"
    HEADERS = "headers"


class AbstractEventSubscriber(ABC):
    """Abstract base class for event subscribers."""

    @abstractmethod
    async def start_consuming(self):
        """Starts consuming messages."""
        ...

    @abstractmethod
    async def stop_consuming(self):
        """Stops consuming messages."""
        ...


class EventSubscriber(AbstractEventSubscriber):
    """
    Consumes messages from RabbitMQ, deserializes them into domain events,
    and dispatches them via a MessageBus. Handles retries with exponential backoff.
    """

    def __init__(
        self,
        connection_manager: AbstractConnectionManager,
        messagebus: MessageBus,
        queue_name: str = '',
        exchange_name: Optional[str] = None,
        exchange_type: ExchangeType = ExchangeType.TOPIC,
        routing_key: Optional[str] = None,
        durable: bool = True,
        prefetch_count: int = 1,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        event_registry: Optional[Dict[str, Type[events.Event]]] = None
    ):
        """
        Initializes the EventSubscriber.

        Args:
            connection_manager (AbstractConnectionManager): AMQP connection manager.
            messagebus (MessageBus): Message bus for event dispatch.
            queue_name (str): The name of the queue to consume from.
            exchange_name (Optional[str]): Name of the exchange to bind to.
            exchange_type (ExchangeType): Type of the exchange. Defaults to TOPIC.
            routing_key (Optional[str]): Routing key for queue binding.
            durable (bool): Whether queue and exchange survive broker restarts. Defaults to True.
            prefetch_count (int): Max number of messages to process concurrently.
            max_retries (int): Max retries for failed messages.
            retry_delay (float): Initial delay in seconds for retries.
            event_registry (Optional[Dict[str, Type[events.Event]]]): Map of event type names to classes.
        """
        if exchange_name and not routing_key and exchange_type != ExchangeType.FANOUT:
            logger.warning(
                f"Exchange '{exchange_name}' provided without a routing key for queue '{queue_name}' "
                f"and is not a FANOUT exchange. Queue might not receive messages."
            )

        self._consuming = False
        self._connection_manager = connection_manager
        self._messagebus = messagebus
        self._stop_event = asyncio.Event()
        self._queue_name = queue_name
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._routing_key = routing_key
        self._durable = durable
        self._prefetch_count = prefetch_count
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._event_registry = event_registry if event_registry is not None else EVENT_REGISTRY

        logger.info(f"EventSubscriber initialized for queue '{self._queue_name}'.")

    async def _setup_queue(self, channel: AbstractRobustChannel) -> AbstractRobustQueue:
        """
        Declares the queue and optionally binds it to an exchange.

        Args:
            channel (AbstractRobustChannel): The channel to declare on.

        Returns:
            AbstractRobustQueue: The declared queue object.
        """
        logger.info(f"Declaring queue '{self._queue_name}' (durable={self._durable}).")
        queue = await channel.declare_queue(
            self._queue_name,
            durable=self._durable
        )

        if self._exchange_name:
            logger.info(
                f"Declaring exchange '{self._exchange_name}' ({self._exchange_type.value}, "
                f"durable={self._durable})."
            )
            exchange = await channel.declare_exchange(
                self._exchange_name,
                aio_pika.ExchangeType(self._exchange_type.value),
                durable=self._durable
            )
            if self._routing_key:
                logger.info(
                    f"Binding queue '{self._queue_name}' to exchange '{self._exchange_name}' "
                    f"with routing key '{self._routing_key}'."
                )
                await queue.bind(exchange, self._routing_key)
            else:
                logger.info(
                    f"Binding queue '{self._queue_name}' to exchange '{self._exchange_name}' "
                    f"without a specific routing key."
                )
                await queue.bind(exchange)

        return queue

    async def _get_retry_delay(self, retry_count: int) -> float:
        """
        Calculates and applies an exponential backoff delay.

        Args:
            retry_count (int): The current retry attempt number.

        Returns:
            float: The calculated delay in seconds.
        """
        delay = self._retry_delay * (2 ** retry_count)
        logger.debug(f"Delaying for {delay:.2f} seconds before retrying.")
        await asyncio.sleep(delay)
        return delay

    async def _handle_message(self, message: AbstractIncomingMessage) -> None:
        """
        Processes an incoming message, manages correlation IDs, and handles acknowledgment.

        Args:
            message (AbstractIncomingMessage): The incoming message.
        """
        headers = dict(message.headers) if message.headers else {}
        retry_count = int(headers.get('x-retry-count', 0))

        correlation_id = headers.get("x-correlation-id")
        if correlation_id:
            logger.debug(f"Correlation ID '{correlation_id}' set from message headers.")
        else:
            correlation_id = str(uuid.uuid4())
            logger.warning(
                f"Message (delivery_tag: {message.delivery_tag}) missing correlation_id. "
                f"Generated: {correlation_id}"
            )
        set_correlation_id(correlation_id)

        try:
            message.headers['x-retry-count'] = retry_count + 1
            result = await self._process_message(message.body, headers)

            if result == ProcessingResult.SUCCESS:
                await message.ack()
                logger.info(f"Message (ID: {message.delivery_tag}, CID: {correlation_id}) acknowledged.")
            elif result == ProcessingResult.REJECTED:
                await message.reject(requeue=False)
                logger.warning(f"Message (ID: {message.delivery_tag}, CID: {correlation_id}) rejected permanently.")
            else:  # ProcessingResult.FAILED
                await self._handle_failure(message, retry_count)

        except Exception as e:
            logger.exception(
                f"Unhandled error processing message (ID: {message.delivery_tag}, CID: {correlation_id}). "
                "Rejecting permanently."
            )
            await message.reject(requeue=False)

    async def _process_message(self, message_body: bytes, headers: Dict[str, Any]) -> ProcessingResult:
        """
        Deserializes message body to an Event and dispatches via message bus.

        Args:
            message_body (bytes): The raw message body.
            headers (Dict[str, Any]): The message headers.

        Returns:
            ProcessingResult: The result of processing.
        """
        try:
            event = self._deserialize(message_body, headers)
            if not event:
                logger.warning(f"Could not deserialize message into a known event. Headers: {headers}")
                return ProcessingResult.REJECTED

            logger.info(f"Dispatching event: {type(event).__name__}.")
            await self._messagebus.handle(event)

            logger.info(f"Event '{type(event).__name__}' processed successfully.")
            return ProcessingResult.SUCCESS

        except Exception as e:
            logger.error(f"Failed to process event: {e}", exc_info=True)
            return ProcessingResult.FAILED

    async def _handle_failure(self, message: AbstractIncomingMessage, retry_count: int) -> None:
        """
        Handles retry logic for failed messages.

        Args:
            message (AbstractIncomingMessage): The failed message.
            retry_count (int): The current retry attempt number.
        """
        if retry_count < self._max_retries:
            logger.warning(
                f"Message (ID: {message.delivery_tag}, CID: {message.correlation_id}) failed. "
                f"Retrying {retry_count + 1}/{self._max_retries}."
            )
            await self._get_retry_delay(retry_count)
            await message.reject(requeue=True)
        else:
            logger.error(
                f"Message (ID: {message.delivery_tag}, CID: {message.correlation_id}) exceeded max retries "
                f"({self._max_retries}). Rejecting permanently."
            )
            await message.reject(requeue=False)

    def _deserialize(self, message_body: bytes, headers: Dict[str, Any]) -> Optional[events.Event]:
        """
        Attempts to deserialize a message into a domain event.

        Args:
            message_body (bytes): The raw message body.
            headers (Dict[str, Any]): The message headers.

        Returns:
            Optional[events.Event]: An event instance, or None if deserialization fails.
        """
        event_type_name = None
        try:
            data = json.loads(message_body.decode('utf-8'))
            event_type_name = headers.get('event_type') or data.get('event_type') or data.get('type')

            if not event_type_name:
                logger.warning("Incoming message missing event type in headers or body. Cannot deserialize.")
                return None

            event_class = self._event_registry.get(event_type_name)
            if not event_class:
                logger.warning(f"Unrecognized event type: '{event_type_name}'. No class in registry.")
                return None

            if hasattr(event_class, 'parse_obj'): # Pydantic v1
                return event_class.parse_obj(data)
            elif hasattr(event_class, 'model_validate'): # Pydantic v2
                return event_class.model_validate(data)
            elif hasattr(event_class, 'from_dict'): # Custom from_dict for dataclasses
                return event_class.from_dict(data)
            else:
                return event_class(**data)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}. Body snippet: {message_body[:200]}...")
            return None
        except Exception as e:
            logger.error(
                f"Deserialization or event instantiation failed for event type '{event_type_name}': {e}",
                exc_info=True
            )
            return None

    async def start_consuming(self):
        """
        Begins consuming messages from the queue. This method blocks until `stop_consuming`
        is called or a fatal error occurs.
        """
        if self._consuming:
            logger.warning(f"Consumer for queue '{self._queue_name}' is already consuming.")
            return

        self._consuming = True
        self._stop_event.clear()

        logger.info(f"Starting consumer for queue '{self._queue_name}'.")
        try:
            async with self._connection_manager.get_dedicated_channel(
                prefetch_count=self._prefetch_count
            ) as channel:
                queue = await self._setup_queue(channel)
                logger.info(
                    f"Consumer started for queue '{self._queue_name}' (prefetch_count={self._prefetch_count})."
                )
                await queue.consume(self._handle_message, no_ack=False)
                await self._stop_event.wait()

        except asyncio.CancelledError:
            logger.info(f"Consumer for queue '{self._queue_name}' was cancelled.")
        except Exception as e:
            logger.exception(f"Fatal error during consumption from queue '{self._queue_name}': {e}")
            raise
        finally:
            self._consuming = False
            logger.info(f"Stopped consuming from queue '{self._queue_name}'.")

    async def stop_consuming(self):
        """
        Signals the consumer to stop receiving messages.
        """
        if not self._consuming:
            logger.warning(f"Stop called for queue '{self._queue_name}' but consumer is idle.")
            return

        logger.info(f"Signaling consumer to stop for queue '{self._queue_name}'.")
        self._stop_event.set()


# Global registry mapping event type names to their corresponding classes.
EVENT_REGISTRY: Dict[str, Type[events.Event]] = {
    # Dynamically populate this at application startup based on your domain events.
    # Example:
    # "UserCreated": events.UserCreated,
    # "OrderPlaced": events.OrderPlaced,
}