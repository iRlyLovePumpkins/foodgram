from http import HTTPStatus

import pytest

from tests.utils import create_recipe, sample_image_data_uri


@pytest.mark.django_db
def test_user_can_upload_and_delete_avatar(user_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    response = user_client.put(
        '/api/users/me/avatar/',
        data={'avatar': sample_image_data_uri()},
        format='json',
    )

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.avatar
    assert response.json()['avatar'] == user.avatar.url

    response = user_client.delete('/api/users/me/avatar/')

    assert response.status_code == HTTPStatus.NO_CONTENT
    user.refresh_from_db()
    assert not user.avatar


@pytest.mark.django_db
def test_recipe_get_link_returns_short_link(user_client, user):
    recipe = create_recipe(user)

    response = user_client.get(
        f'/api/recipes/{recipe.id}/get-link/'
    )

    assert response.status_code == HTTPStatus.OK
    short_link = response.json()['short-link']
    assert short_link.endswith(f'/s/{recipe.id:x}/')
