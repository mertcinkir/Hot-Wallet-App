import logging
from src.domain import commands
from src.core.events import events
from src.core.exceptions.exceptions import InvalidMessageTypeException
from typing import Callable, Dict, List, Union, Type, TYPE_CHECKING


if TYPE_CHECKING:
    from src.service_layer.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)
Message = Union[commands.Command, events.Event]


class MessageBus:
    """
    Coordinates the dispatching of commands and events to their respective handlers.

    This class acts as the central hub for processing application messages,
    ensuring that commands are handled by a single designated handler and
    events are dispatched to all subscribed handlers. It also manages the
    collection and propagation of new events generated during message processing.

    Attributes:
        puow (AbstractUnitOfWork): The unit of work instance to handle persistence
                                  and collect domain events.
        event_handlers (Dict[Type[events.Event], List[Callable]]): A mapping
                                  of event types to a list of their corresponding handlers.
        command_handlers (Dict[Type[commands.Command], Callable]): A mapping
                                  of command types to their single designated handler.
    """

    def __init__(
        self,
        puow: "AbstractUnitOfWork",
        event_handlers: Dict[Type[events.Event], List[Callable]],
        command_handlers: Dict[Type[commands.Command], Callable],
    ):
        self.puow = puow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.queue: List[Message] = [] # Initialize the internal message queue

    async def handle(self, message: Message):
        """
        Handles an incoming message, which can be either a Command or an Event.

        This method places the initial message into an internal queue and then
        processes messages one by one. If a handler generates new events,
        those events are added to the queue for subsequent processing.

        Args:
            message (Message): The initial command or event to be processed.

        Raises:
            InvalidMessageTypeException: If the received message is neither
                                         a Command nor an Event.
        """
        self.queue = [message] # Reset queue for each new top-level handle call
        while self.queue:
            current_message = self.queue.pop(0)
            logger.info(f"Processing message: {type(current_message).__name__}")

            if isinstance(current_message, events.Event):
                await self.handle_event(current_message)
            elif isinstance(current_message, commands.Command):
                await self.handle_command(current_message)
            else:
                logger.error(f"Received an invalid message type: {type(current_message).__name__}")
                raise InvalidMessageTypeException(msg=f"{current_message} was not an Event or Command")

    async def handle_event(self, event: events.Event):
        """
        Dispatches an event to all of its registered handlers.

        After each handler processes the event, any new domain events collected
        by the Unit of Work are added to the message bus's internal queue
        for further processing.

        Args:
            event (events.Event): The event instance to be handled.
        """
        event_type_name = type(event).__name__
        logger.debug(f"Handling event: {event_type_name}")

        handlers_for_event = self.event_handlers.get(type(event), [])
        if not handlers_for_event:
            logger.warning(f"No handlers registered for event: {event_type_name}")
            return

        for handler in handlers_for_event:
            try:
                await handler(event)
                # Collect and enqueue any new events raised by the handler
                self.queue.extend(self.puow.collect_new_events())
            except Exception as e:
                logger.exception(f"Error handling event '{event_type_name}'")
                # Depending on the error handling strategy, you might re-raise,
                # publish a new error event, or log and continue.

    async def handle_command(self, command: commands.Command):
        """
        Dispatches a command to its single registered handler.

        After the command handler processes the command, any new domain events
        collected by the Unit of Work are added to the message bus's internal
        queue for subsequent processing.

        Args:
            command (commands.Command): The command instance to be handled.
        """
        command_type_name = type(command).__name__
        logger.debug(f"Handling command: {command_type_name}")

        handler = self.command_handlers.get(type(command))
        if not handler:
            logger.error(f"No handler registered for command: {command_type_name}")
            raise ValueError(f"No handler registered for command type: {command_type_name}")

        try:
            await handler(command)
            # Collect and enqueue any new events raised by the handler
            self.queue.extend(self.puow.collect_new_events())
        except Exception as e:
            logger.error(f"Error handling command '{command_type_name}'")
            raise # Re-raise the exception to be handled by higher layers (e.g., FastAPI exception handlers)