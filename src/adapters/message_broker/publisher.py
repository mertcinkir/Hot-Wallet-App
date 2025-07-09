import json
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import aio_pika
from aio_pika.abc import DeliveryMode
from src.adapters.message_broker.connection_manager import AbstractConnectionManager
from src.core.correlation.context import get_correlation_id
from src.core.exceptions.exceptions import EventSerializationException, ConnectionClosedException

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Defines priority levels for messages."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class MessageOptions:
    """Encapsulates various options for publishing an AMQP message."""
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_ms: Optional[int] = None
    headers: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    message_id: Optional[str] = None
    expiration: Optional[str] = None
    mandatory: bool = False
    immediate: bool = False

    def to_aio_pika_message(self, body: bytes) -> aio_pika.Message:
        """
        Converts the message options and body into an `aio_pika.Message` object.
        """
        return aio_pika.Message(
            body=body,
            priority=self.priority.value,
            delivery_mode=DeliveryMode.PERSISTENT,
            headers=self.headers or {},
            correlation_id=self.correlation_id,
            reply_to=self.reply_to,
            message_id=self.message_id,
            content_type="application/json",
            content_encoding="utf-8",
            expiration=self.expiration,
            timestamp=time.time(),
        )


class PublishResult:
    """Represents the outcome of a message publishing operation."""

    def __init__(
            self,
            success: bool,
            message_id: Optional[str] = None,
            publish_time_ms: float = 0.0,
    ):
        self.success = success
        self.message_id = message_id
        self.publish_time_ms = publish_time_ms
        self.timestamp = time.time()


class AbstractEventPublisher(ABC):
    """Abstract base class for event publishers."""

    @abstractmethod
    async def publish_event(
            self,
            event: Any,
            options: Optional[MessageOptions] = None
    ) -> PublishResult:
        """Publishes a single event."""
        pass

    @abstractmethod
    async def publish_events_batch(
            self,
            events: List[Tuple[str, Any, Optional[MessageOptions]]]
    ) -> List[PublishResult]:
        """Publishes multiple events in a batch."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes the publisher and cleans up resources."""
        pass


class EventPublisher(AbstractEventPublisher):
    """
    Publishes Pydantic dataclass events to RabbitMQ with retry logic and batching capabilities.
    """

    def __init__(
            self,
            connection_manager: AbstractConnectionManager,
            max_retries: int = 3,
            retry_delay_ms: int = 100,
            batch_size: int = 100,
            publish_timeout: float = 5.0
    ):
        """
        Initializes the EventPublisher.

        Args:
            connection_manager (AbstractConnectionManager): AMQP connection manager.
            max_retries (int): Maximum number of retries for publishing.
            retry_delay_ms (int): Delay in milliseconds between retries.
            batch_size (int): Number of events to process per batch.
            publish_timeout (float): Timeout in seconds for a single publish operation.
        """
        self._connection_manager = connection_manager
        self._max_retries = max_retries
        self._retry_delay_ms = retry_delay_ms
        self._batch_size = batch_size
        self._publish_timeout = publish_timeout
        self._closed = False

        logger.info("RabbitMQ Event Publisher initialized.")

    @staticmethod
    def _serialize_event(event: Any) -> bytes:
        """
        Serializes a Pydantic or dataclass event to JSON bytes.

        Args:
            event (Any): The event object to serialize.

        Returns:
            bytes: The JSON representation of the event as bytes.

        Raises:
            EventSerializationException: If serialization fails.
        """
        try:
            if hasattr(event, '__pydantic_serializer__'):
                json_data = event.__pydantic_serializer__.to_json(event)
                return json_data if isinstance(json_data, bytes) else json_data.encode('utf-8')
            elif hasattr(event, '__dataclass_fields__'):
                from dataclasses import asdict
                event_dict = asdict(event)
                return json.dumps(event_dict, default=str, ensure_ascii=False).encode('utf-8')
            else:
                return json.dumps(event, default=str, ensure_ascii=False).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize event type '{type(event).__name__}': {e}")
            raise EventSerializationException(
                msg=f"Cannot serialize event of type '{type(event).__name__}': {e}"
            )

    def _prepare_message(
            self,
            event: Any,
            options: Optional[MessageOptions] = None
    ) -> Tuple[aio_pika.Message, MessageOptions]:
        """
        Prepares an `aio_pika.Message` from an event and publishing options.

        Args:
            event (Any): The event object.
            options (Optional[MessageOptions]): Publishing options.

        Returns:
            Tuple[aio_pika.Message, MessageOptions]: The prepared aio_pika message
                                                    and the finalized options.
        """
        if options is None:
            options = MessageOptions()

        body = self._serialize_event(event)

        if not options.message_id:
            event_type = type(event).__name__
            options.message_id = f"{event_type}_{int(time.time() * 1000)}_{id(event)}"

        if not options.headers:
            options.headers = {}
        options.headers['event_type'] = type(event).__name__
        options.headers["x-correlation-id"] = get_correlation_id()

        aio_pika_message = options.to_aio_pika_message(body)

        return aio_pika_message, options

    async def _publish_with_retry(
            self,
            event: Any,
            options: Optional[MessageOptions]
    ) -> PublishResult:
        """
        Publishes a message with retry logic.

        Args:
            event (Any): The event object to publish. Must have 'source_service' and 'event_type' attributes.
            options (Optional[MessageOptions]): Publishing options.

        Returns:
            PublishResult: The result of the publish operation.
        """
        exchange_name = f"{event.source_service}.events"
        aio_pika_message, final_options = self._prepare_message(event, options)

        for attempt in range(self._max_retries + 1):
            try:
                start_time = time.time()
                async with self._connection_manager.get_channel() as channel:
                    exchange = await channel.declare_exchange(
                        exchange_name,
                        aio_pika.ExchangeType.TOPIC,
                        durable=True
                    )

                    await exchange.publish(
                        aio_pika_message,
                        routing_key=event.event_type,
                        mandatory=final_options.mandatory,
                        immediate=final_options.immediate,
                        timeout=self._publish_timeout
                    )

                publish_time_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Message '{final_options.message_id}' for event '{type(event).__name__}' "
                    f"published to '{exchange_name}' in {publish_time_ms:.2f} ms. (Attempt: {attempt + 1})"
                )
                return PublishResult(
                    success=True,
                    message_id=final_options.message_id,
                    publish_time_ms=publish_time_ms,
                )
            except aio_pika.exceptions.DeliveryError as e:
                logger.error(f"Delivery error for message '{final_options.message_id}': {e}. (Attempt: {attempt + 1})")
            except asyncio.TimeoutError:
                logger.error(f"Publish timeout for message '{final_options.message_id}'. (Attempt: {attempt + 1})")
            except ConnectionClosedException as e:
                logger.error(f"Connection closed during publish for message '{final_options.message_id}': {e}. (Attempt: {attempt + 1})")
            except Exception as e:
                logger.error(
                    f"Unexpected error during publish attempt {attempt + 1} for message '{final_options.message_id}': {e}",
                    exc_info=True
                )

            if attempt < self._max_retries:
                retry_delay_sec = self._retry_delay_ms / 1000.0
                logger.warning(
                    f"Retrying publish for message '{final_options.message_id}' in {retry_delay_sec:.2f}s."
                )
                await asyncio.sleep(retry_delay_sec)
            else:
                logger.error(
                    f"Max retries ({self._max_retries}) exceeded for message '{final_options.message_id}'. "
                    "Publish failed permanently."
                )
                break

        return PublishResult(
            success=False,
            message_id=final_options.message_id,
        )

    async def publish_event(
            self,
            event: Any,
            options: Optional[MessageOptions] = None
    ) -> PublishResult:
        """
        Publishes a single event using retry logic.

        Args:
            event (Any): The event object to publish.
            options (Optional[MessageOptions]): Optional message publishing options.

        Returns:
            PublishResult: The result of the publish operation.

        Raises:
            ConnectionClosedException: If the publisher has been closed.
        """
        if self._closed:
            logger.error("Attempted to publish event while publisher is closed.")
            raise ConnectionClosedException(msg="Publisher is closed")

        try:
            result = await self._publish_with_retry(event, options)
            return result
        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)
            return PublishResult(
                success=False,
                message_id=options.message_id if options else None
            )

    async def publish_events_batch(
            self,
            events: List[Tuple[str, Any, Optional[MessageOptions]]]
    ) -> List[PublishResult]:
        """
        Publishes a list of events in configurable batches.

        Args:
            events (List[Tuple[str, Any, Optional[MessageOptions]]]): A list of events to publish.
                Each tuple contains (routing_key, event_object, MessageOptions).

        Returns:
            List[PublishResult]: A list of results for each event.

        Raises:
            ConnectionClosedException: If the publisher has been closed.
        """
        if self._closed:
            logger.error("Attempted to publish event batch while publisher is closed.")
            raise ConnectionClosedException(msg="Publisher is closed")

        results = []

        for i in range(0, len(events), self._batch_size):
            batch = events[i:i + self._batch_size]
            # _publish_with_retry expects (event, options), not (routing_key, event, options)
            batch_results = await self._publish_batch_chunk([(e, o) for _, e, o in batch])
            results.extend(batch_results)

        return results

    async def _publish_batch_chunk(
            self,
            events: List[Tuple[Any, Optional[MessageOptions]]]
    ) -> List[PublishResult]:
        """
        Internal helper to publish a chunk of events concurrently.

        Args:
            events (List[Tuple[Any, Optional[MessageOptions]]]): A list of (event, options) tuples.

        Returns:
            List[PublishResult]: A list of results for each event in the chunk.
        """
        results = []
        publish_tasks = [self._publish_with_retry(event, options) for event, options in events]

        batch_results = await asyncio.gather(*publish_tasks, return_exceptions=True)

        for res in batch_results:
            if isinstance(res, Exception):
                logger.error(f"An error occurred in a batch publish task: {res}", exc_info=True)
                results.append(PublishResult(success=False, message_id=None))
            else:
                results.append(res)

        return results

    async def close(self) -> None:
        """
        Sets the publisher to a closed state, preventing further publish operations.
        """
        self._closed = True
        logger.info("RabbitMQ Event Publisher closed.")
