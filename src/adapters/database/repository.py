from abc import ABC, abstractmethod
from typing import Set, Union, Callable
from sqlalchemy.orm import Query, Session
from src.domain.model import User, UserID, Username, Email


def check_excluded_userid(func: Callable) -> Callable:
    """
    Decorator to modify a query for username/email uniqueness checks.

    It adds a filter to exclude a specific user ID, useful for update scenarios.
    """
    def wrapper(self, value: Union[Username, str], exclude_userid: Union[UserID, str] = None) -> bool:
        query = func(self, value, exclude_userid)
        if exclude_userid:
            exclude_userid = exclude_userid if isinstance(exclude_userid, UserID) else UserID(exclude_userid)
            query = query.filter(User.userid != exclude_userid)
        return self.session.query(query.exists()).scalar()
    return wrapper


class AbstractRepository(ABC):
    """
    Abstract base class for a repository.

    Defines the interface for interacting with user data and tracks
    'seen' entities for Unit of a Work event collection.
    """

    def __init__(self):
        self.seen = set()  # type: Set[User]

    def add(self, user: User):
        """
        Adds a user to the repository and marks it as seen.
        """
        self._add(user)
        self.seen.add(user)

    def get(self, user_id: Union[UserID, str]) -> User | None:
        """
        Retrieves a user by their ID and marks it as seen if found.
        """
        user = self._get(user_id)
        if user:
            self.seen.add(user)
        return user

    def get_by_username(self, username: Union[Username, str]) -> User | None:
        """
        Retrieves a user by their username and marks it as seen if found.
        """
        user = self._get_by_username(username)
        if user:
            self.seen.add(user)
        return user

    @abstractmethod
    def _add(self, user: User):
        """
        Abstract method to add a user to the persistence layer.
        """
        raise NotImplementedError

    @abstractmethod
    def _get(self, user_id: Union[UserID, str]) -> User | None:
        """
        Abstract method to retrieve a user by ID from the persistence layer.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_by_username(self, username: Union[Username, str]) -> User | None:
        """
        Abstract method to retrieve a user by username from the persistence layer.
        """
        raise NotImplementedError

    @abstractmethod
    def is_username_taken(self, username: Union[Username, str], exclude_user_id: Union[UserID, str] = None) -> bool:
        """
        Abstract method to check if a username is already taken.
        Optionally excludes a specific user ID from the check.
        """
        raise NotImplementedError

    @abstractmethod
    def is_email_taken(self, email: Union[Email, str], exclude_user_id: Union[UserID, str] = None) -> bool:
        """
        Abstract method to check if an email is already taken.
        Optionally excludes a specific user ID from the check.
        """
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """
    SQLAlchemy implementation of the AbstractRepository for User entities.
    """

    def __init__(self, session: Session):
        """
        Initializes the SQLAlchemy repository with a database session.
        """
        super().__init__()
        self.session = session

    def _add(self, user: User):
        """
        Adds a User entity to the SQLAlchemy session.
        """
        self.session.add(user)

    def _get(self, userid: Union[UserID, str]) -> User | None:
        """
        Retrieves a User entity by ID from the database using SQLAlchemy.
        """
        userid = userid if isinstance(userid, UserID) else UserID(userid)
        return self.session.query(User).filter(User.userid == userid).first()

    def _get_by_username(self, username: Union[Username, str]) -> User | None:
        """
        Retrieves a User entity by username from the database using SQLAlchemy.
        """
        username = username if isinstance(username, Username) else Username(username)
        return self.session.query(User).filter(User.username == username).first()

    @check_excluded_userid
    def is_username_taken(self, username: Union[Username, str], exclude_userid: Union[UserID, str] = None) -> Query:
        """
        Checks if a username is taken, returning a SQLAlchemy Query object.
        The decorator `check_excluded_userid` processes this query to return a boolean.
        """
        username = username if isinstance(username, Username) else Username(username)
        return self.session.query(User).filter(User.username == username)

    @check_excluded_userid
    def is_email_taken(self, email: Union[Email, str], exclude_userid: Union[UserID, str] = None) -> Query:
        """
        Checks if an email is taken, returning a SQLAlchemy Query object.
        The decorator `check_excluded_userid` processes this query to return a boolean.
        """
        email = email if isinstance(email, Email) else Email(email)
        return self.session.query(User).filter(User.email == email)