import inspect
from src.service_layer import handlers, messagebus, unit_of_work
from src.adapters.message_broker import connection_manager, publisher


def bootstrap(
        puow: unit_of_work.AbstractUnitOfWork = None,
        suow: unit_of_work.AbstractUnitOfWork = None,
        conn: connection_manager.AbstractConnectionManager = None,
        pub: publisher.AbstractEventPublisher = None
) -> messagebus.MessageBus:
    """
        initializes and configures the message bus with dependency-injected handlers.

        this function sets up the core components of the application's service layer,
        including the Unit of Work, connection manager, and event publisher. It
        then injects these dependencies into the appropriate event and command handlers.

        Args:
            puow (unit_of_work.AbstractUnitOfWork, optional): The Unit of Work instance
                for primary database operations. Defaults to None.
            suow (unit_of_work.AbstractUnitOfWork, optional): The Unit of Work instance
                for standby database operations. Defaults to None.
            conn (connection_manager.AbstractConnectionManager, optional): The connection
                manager for message broker interactions. Defaults to None.
            pub (publisher.AbstractEventPublisher, optional): The event publisher
                for sending domain events. Defaults to None.

        Returns:
            messagebus.MessageBus: An initialized MessageBus instance ready to handle
                commands and events.
        """
    dependencies = {"puow": puow, "suow": suow, "conn":conn, "pub": pub}
    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies)
            for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    return messagebus.MessageBus(
        puow=puow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
    )


def inject_dependencies(handler, dependencies):
    """
    Injects specified dependencies into a handler function.

    This utility function inspects the signature of the `handler` and
    creates a new callable that automatically passes the matching
    dependencies from the `dependencies` dictionary to the handler
    when it's called.

    Args:
        handler (callable): The function or method to inject dependencies into.
        dependencies (dict): A dictionary where keys are dependency names (str)
            and values are the dependency objects.

    Returns:
        callable: A new callable that wraps the original handler,
            pre-populating its arguments with injected dependencies.
    """
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return lambda message: handler(message, **deps)
