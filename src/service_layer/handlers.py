import logging
from src.domain import commands
from src.service_layer import unit_of_work
from src.adapters.message_broker import publisher
from src.domain.model import User  # Assuming 'User' is the main model needed
from src.core.exceptions.exceptions import EmailAlreadyRegisteredException, UsernameAlreadyRegisteredException
from src.core.events import events
from uuid import uuid4
from argon2 import PasswordHasher

logger = logging.getLogger(__name__)


async def register_user_handler(
        cmd: commands.UserRegisterCommand,
        puow: unit_of_work.AbstractUnitOfWork
):
    """
    Handles the UserRegisterCommand to register a new user.

    This handler performs the following steps:
    1. Check if the provided username is already taken.
    2. Check if the provided email is already registered.
    3. Hash the user's password.
    4. Create a new User entity.
    5. Add the new user to the repository and commit the transaction.

    Args:
        cmd (commands.UserRegisterCommand): The command containing user registration details.
        puow (unit_of_work.AbstractUnitOfWork): The unit of work for managing database transactions.

    Raises:
        UsernameAlreadyRegisteredException: If the username is already in use.
        EmailAlreadyRegisteredException: If the email is already registered.
    """
    with puow:
        if puow.users.is_username_taken(cmd.username):
            logger.warning(f"Registration failed: Username '{cmd.username}' is already taken.")
            raise UsernameAlreadyRegisteredException()
        if puow.users.is_email_taken(cmd.email):
            logger.warning(f"Registration failed: Email '{cmd.email}' is already registered.")
            raise EmailAlreadyRegisteredException()

        # Hash the password before creating the user
        ph = PasswordHasher()
        hashed_password = ph.hash(cmd.password)

        user = User.create(
            uuid4().hex,  # Generate a unique ID for the user
            cmd.username,
            cmd.email,
            hashed_password,
            verified_flag=False,  # New users are typically not active until email verification
        )
        puow.users.add(user)
        puow.commit()
        logger.info(f"User '{cmd.username}' successfully registered with ID: {user.userid}")


async def email_registration_requested_handler(
        event: events.UserEmailVerificationRequested,
        pub: publisher.AbstractEventPublisher
):
    """
    Handles the UserEmailVerificationRequested event by publishing it to the message broker.

    This handler is responsible for forwarding the event, which typically triggers
    an email verification process.

    Args:
        event (events.UserEmailVerificationRequested): The event containing details for email verification.
        pub (publisher.AbstractEventPublisher): The event publisher for sending the event to the message broker.
    """
    logger.info(f"Publishing UserEmailVerificationRequested event for user ID: {event.userid}")
    await pub.publish_event(event)



"""
These dictionaries map commands and events to their respective handler functions.
This setup allows the message bus to dispatch incoming commands and events to the correct processing logic.
"""

COMMAND_HANDLERS = {
    commands.UserRegisterCommand: register_user_handler,
}

EVENT_HANDLERS = {
    events.UserEmailVerificationRequested: {email_registration_requested_handler}
}
