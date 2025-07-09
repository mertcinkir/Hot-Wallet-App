from uuid import uuid4


# Test örnekleri
def test_register_with_uow(sqlalchemy_unit_of_work, user_factory):
    uid = uuid4().hex
    user = user_factory(userid=uid)
    with sqlalchemy_unit_of_work as uow:
        uow.users.add(user)
        uow.commit()

    with sqlalchemy_unit_of_work as uow:
        assert uow.users.get(uid) is not None

def test_rollback_mechanism(sqlalchemy_unit_of_work, user_factory):
    uid = uuid4().hex
    user = user_factory(userid=uid)
    with sqlalchemy_unit_of_work as uow:
        uow.users.add(user)

    with sqlalchemy_unit_of_work as uow:
        assert uow.users.get(uid) is None
