from http import HTTPStatus

import pytest

from tests.utils import check_pagination

USERS_URL = '/api/users/'
USERS_ME_URL = '/api/users/me/'


def serialized_user(user, is_subscribed=False):
    return {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'avatar': None,
        'is_subscribed': is_subscribed,
    }


@pytest.mark.django_db
def test_user_list_is_public_and_paginated(client, user):
    response = client.get(USERS_URL)

    assert response.status_code == HTTPStatus.OK
    check_pagination(
        USERS_URL,
        response.json(),
        expected_count=1,
        post_data=serialized_user(user),
    )


@pytest.mark.django_db
def test_user_detail_uses_id_lookup(client, user):
    response = client.get(f'{USERS_URL}{user.id}/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == serialized_user(user)


@pytest.mark.django_db
def test_me_requires_authentication(client):
    response = client.get(USERS_ME_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_me_can_read_and_update_own_names(user_client, user):
    response = user_client.get(USERS_ME_URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == serialized_user(user)

    response = user_client.patch(
        USERS_ME_URL,
        data={'first_name': 'Updated', 'last_name': 'Cook'},
        format='json',
    )

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.first_name == 'Updated'
    assert user.last_name == 'Cook'


@pytest.mark.django_db
def test_users_can_subscribe_and_unsubscribe(user_client, user, admin):
    url = f'{USERS_URL}{admin.id}/subscribe/'

    response = user_client.post(url)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['id'] == admin.id
    assert user.subscriptions.filter(pk=admin.pk).exists()

    duplicate_response = user_client.post(url)
    assert duplicate_response.status_code == HTTPStatus.BAD_REQUEST

    response = user_client.delete(url)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not user.subscriptions.filter(pk=admin.pk).exists()


@pytest.mark.django_db
def test_cannot_subscribe_to_self(user_client, user):
    response = user_client.post(f'{USERS_URL}{user.id}/subscribe/')

    assert response.status_code == HTTPStatus.BAD_REQUEST
