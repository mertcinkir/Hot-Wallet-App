def test_is_username_taken(sqlalchemy_repository, user_factory):
    user_factory(sqlalchemy_repository, username='tester')
    assert sqlalchemy_repository.is_username_taken('tester') == True


def test_is_email_taken(sqlalchemy_repository, user_factory):
    user_factory(sqlalchemy_repository, email='test@example.com')
    assert sqlalchemy_repository.is_email_taken('test@example.com') == True