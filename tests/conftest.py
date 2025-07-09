# tests/conftest.py
import pytest
from uuid import uuid4
from argon2 import PasswordHasher
from src.domain.model import User
from src.bootstrap import bootstrap
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers
from src.adapters.database.orm import init_orm_mappers, metadata
from src.adapters.database.repository import SqlAlchemyRepository, AbstractRepository
from src.service_layer.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork


class FakeRepository(AbstractRepository):
    def __init__(self, users):
        super().__init__()
        self._users = set(users)

    def _add(self, user):
        self._users.add(user)

    def _get(self, userid):
        return next((u for u in self._users if u.userid == userid), None)

    def _get_by_username(self, username):
        return next(
            (u for u in self._users if u.username.value == username),
            None,
        )

    def is_username_taken(self, username: str, exclude_user_id: int = None) -> bool:
        return next(
            (True for u in self._users if u.username.value == username and u.userid != exclude_user_id),
            False,
        )

    def is_email_taken(self, email: str, exclude_user_id: int = None) -> bool:
        return next(
            (True for u in self._users if u.email.value == email and u.userid != exclude_user_id),
            False,
        )

class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.users = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


@pytest.fixture(scope="function")
def sqlite_engine():
    # SQLite bellek veritabanı ve tablo oluşturma
    engine = create_engine("sqlite:///:memory:", echo=True)
    metadata.create_all(engine)
    yield engine
    metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sqlite_session_factory(sqlite_engine):
    return sessionmaker(bind=sqlite_engine)


@pytest.fixture(scope="function")
def sqlalchemy_repository(sqlite_session_factory):
    clear_mappers()
    init_orm_mappers()
    return SqlAlchemyRepository(sqlite_session_factory())


@pytest.fixture(scope="function")
def sqlalchemy_unit_of_work(sqlite_session_factory):
    clear_mappers()
    init_orm_mappers()
    return SqlAlchemyUnitOfWork(sqlite_session_factory)


@pytest.fixture(scope="function")
def sqlalchemy_messagebus(sqlalchemy_unit_of_work):
    return bootstrap(
        start_orm=False,
        uow=sqlalchemy_unit_of_work
    )


@pytest.fixture(scope="function")
def fake_repository():
    return FakeRepository([])


@pytest.fixture(scope="function")
def fake_unit_of_work():
    return FakeUnitOfWork()


@pytest.fixture(scope="function")
def fake_messagebus(fake_unit_of_work):
    return bootstrap(
        start_orm=False,
        uow=fake_unit_of_work
    )


@pytest.fixture(scope="function")
def user_factory():
    def factory(repository=None, **overrides):
        ph = PasswordHasher()
        defaults = {
            "userid": uuid4().hex,
            "username": "tester",
            "email": "test@example.com",
            "password_hash": ph.hash("qQ@12345678"),
            "verified_flag": False,
        }
        merged = {**defaults, **overrides}
        user = User.create(**merged)
        if repository:
            repository.add(user)
            repository.session.commit()
        return user
    return factory
