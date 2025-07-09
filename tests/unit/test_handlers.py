import pytest

@pytest.mark.asyncio
async def test_register_for_new_user(fake_messagebus):
    from src.domain.commands import UserRegisterCommand
    cmd = UserRegisterCommand(
        "tester",
        "Tester Testerson",
        "test@example.com",
        "1234567890"
    )
    await fake_messagebus.handle(cmd)
    assert fake_messagebus.uow.users.get_by_username(cmd.username) is not None
    assert fake_messagebus.uow.committed