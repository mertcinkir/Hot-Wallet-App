import contextvars

# Define a ContextVar named "correlation_id" with a default value of None.
# ContextVars are designed to manage context-local state in asynchronous code,
# ensuring that a value set in one async task doesn't leak into another,
# unless explicitly propagated.
correlation_id_var = contextvars.ContextVar("correlation_id", default=None)

def get_correlation_id() -> str | None:
    """
    Retrieves the correlation ID from the current context.

    Returns:
        str | None: The correlation ID if set, otherwise None.
    """
    return correlation_id_var.get()

def set_correlation_id(value: str):
    """
    Sets the correlation ID for the current context.

    Args:
        value (str): The string value to set as the correlation ID.
    """
    correlation_id_var.set(value)
