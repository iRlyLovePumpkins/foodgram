import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


@pytest.fixture
def user_superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username='TestSuperuser',
        first_name='a',
        last_name='b',
        email='testsuperuser@foodgram.fake',
        password='1234567',
    )


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_user(
        username='TestAdmin',
        first_name='c',
        last_name='d',
        email='testadmin@foodgram.fake',
        password='1234567',
    )



@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username='TestUser',
        first_name='e',
        last_name='f',
        email='testuser@foodgram.fake',
        password='1234567',
    )


@pytest.fixture
def token_user_superuser(user_superuser):
    token, _ = Token.objects.get_or_create(user=user_superuser)
    return {
        'Authorization': f'Token {token.key}',
    }


@pytest.fixture
def user_superuser_client(token_user_superuser):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=token_user_superuser['Authorization']
    )
    return client


@pytest.fixture
def token_admin(admin):
    token, _ = Token.objects.get_or_create(user=admin)
    return {
        'Authorization': f'Token {token.key}',
    }


@pytest.fixture
def admin_client(token_admin):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=token_admin['Authorization']
    )
    return client


@pytest.fixture
def token_user(user):
    token, _= Token.objects.get_or_create(user=user)
    return {
        'Authorization': f'Token {token.key}',
    }


@pytest.fixture
def user_client(token_user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=token_user['Authorization']
    )
    return client
