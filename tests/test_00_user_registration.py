from http import HTTPStatus

import pytest

from tests.utils import invalid_data_for_user_patch_and_creation

USERS_URL = '/api/users/'
TOKEN_URL = '/api/auth/token/login/'


@pytest.mark.django_db
def test_user_creation_requires_model_fields(client):
    response = client.post(USERS_URL, data={})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert {'email', 'username', 'first_name', 'last_name', 'password'} <= set(
        response.json()
    )


@pytest.mark.django_db
def test_user_creation_and_email_login(client, django_user_model):
    user_data = {
        'email': 'new-user@foodgram.fake',
        'username': 'new_user',
        'first_name': 'New',
        'last_name': 'Cook',
        'password': 'test-password-123',
    }

    response = client.post(USERS_URL, data=user_data)

    assert response.status_code == HTTPStatus.CREATED
    response_data = response.json()
    assert response_data['email'] == user_data['email']
    assert response_data['username'] == user_data['username']
    assert 'password' not in response_data
    assert django_user_model.objects.filter(email=user_data['email']).exists()

    token_response = client.post(
        TOKEN_URL,
        data={'email': user_data['email'], 'password': user_data['password']},
    )
    assert token_response.status_code == HTTPStatus.OK
    assert token_response.json().get('auth_token')


@pytest.mark.django_db
@pytest.mark.parametrize(
    'data,reason', invalid_data_for_user_patch_and_creation
)
def test_user_creation_rejects_invalid_model_values(client, data, reason):
    response = client.post(USERS_URL, data=data)

    assert response.status_code == HTTPStatus.BAD_REQUEST, reason


@pytest.mark.django_db
def test_user_email_must_be_unique(client, user):
    response = client.post(
        USERS_URL,
        data={
            'email': user.email,
            'username': 'another_user',
            'first_name': 'Another',
            'last_name': 'Cook',
            'password': 'test-password-123',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'email' in response.json()
