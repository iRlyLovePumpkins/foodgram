from http import HTTPStatus

import pytest

from tests.utils import create_recipe, create_shopping_cart_item


RECIPES_URL = '/api/recipes/'


@pytest.mark.django_db
def test_recipe_shopping_cart_and_download(user_client, user):
    recipe = create_recipe(user)
    url = f'{RECIPES_URL}{recipe.id}/shopping_cart/'

    response = user_client.post(url)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['id'] == recipe.id

    duplicate_response = user_client.post(url)
    assert duplicate_response.status_code == HTTPStatus.BAD_REQUEST

    download_response = user_client.get(
        f'{RECIPES_URL}download_shopping_cart/'
    )
    assert download_response.status_code == HTTPStatus.OK
    assert b'Oats' in download_response.content

    response = user_client.delete(url)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not user.shopping_cart.filter(recipe=recipe).exists()


@pytest.mark.django_db
def test_shopping_cart_filter(user_client, user):
    recipe = create_recipe(user)
    create_shopping_cart_item(user, recipe)

    response = user_client.get(f'{RECIPES_URL}?is_in_shopping_cart=1')

    assert response.status_code == HTTPStatus.OK
    assert recipe.id in [item['id'] for item in response.json()['results']]


@pytest.mark.django_db
def test_shopping_cart_requires_authentication(client, user):
    recipe = create_recipe(user)

    response = client.post(
        f'{RECIPES_URL}{recipe.id}/shopping_cart/'
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED