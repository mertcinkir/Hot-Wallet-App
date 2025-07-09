from fastapi import APIRouter, status, Depends, Request
from src.domain.commands import UserRegisterCommand
from src.service_layer.messagebus import MessageBus


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Source not found."}},
)

def get_messagebus(request: Request) -> MessageBus:
    """
    Retrieves the MessageBus instance from the FastAPI application state.

    Returns:
        MessageBus: The MessageBus instance used for handling commands and events.
    """
    return request.app.state.messagebus

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
        cmd: UserRegisterCommand,
        messagebus: MessageBus = Depends(get_messagebus),
):
    """
    Registers a new user by sending a UserRegisterCommand to the message bus.

    Returns:
        str: A simple "OK" message indicating successful command processing.
    """
    await messagebus.handle(cmd)
    return "OK"
