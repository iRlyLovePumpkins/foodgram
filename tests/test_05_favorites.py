from http import HTTPStatus

import pytest

from tests.utils import create_recipe

RECIPES_URL = '/api/recipes/'


@pytest.mark.django_db
def test_recipe_can_be_added_to_and_removed_from_favorites(
    user_client, user
):
    recipe = create_recipe(user)
    url = f'{RECIPES_URL}{recipe.id}/favorite/'

    response = user_client.post(url)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['id'] == recipe.id
    assert user.favorites.filter(pk=recipe.pk).exists()

    duplicate_response = user_client.post(url)
    assert duplicate_response.status_code == HTTPStatus.BAD_REQUEST

    response = user_client.get(f'{RECIPES_URL}?is_favorited=1')
    assert response.status_code == HTTPStatus.OK
    assert recipe.id in [item['id'] for item in response.json()['results']]

    response = user_client.delete(url)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not user.favorites.filter(pk=recipe.pk).exists()


@pytest.mark.django_db
def test_favorites_require_authentication(client, user):
    recipe = create_recipe(user)

    response = client.post(f'{RECIPES_URL}{recipe.id}/favorite/')

    assert response.status_code == HTTPStatus.UNAUTHORIZED