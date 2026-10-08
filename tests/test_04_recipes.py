from http import HTTPStatus

import pytest

from tests.utils import (
    check_pagination,
    create_ingredients,
    create_recipe,
    create_recipes,
    create_single_recipe,
    create_tags,
    recipe_payload,
)

RECIPES_URL = '/api/recipes/'


@pytest.mark.django_db
def test_recipes_are_public_and_paginated(client, user):
    recipes = create_recipes(user)

    response = client.get(RECIPES_URL)

    assert response.status_code == HTTPStatus.OK
    check_pagination(RECIPES_URL, response.json(), expected_count=2)

    recipe_data = response.json()['results'][0]
    assert {'id', 'name', 'author', 'tags', 'ingredients', 'image'} <= set(
        recipe_data
    )
    detail_response = client.get(f'{RECIPES_URL}{recipes[0].id}/')
    assert detail_response.status_code == HTTPStatus.OK
    assert detail_response.json()['id'] == recipes[0].id


@pytest.mark.django_db
def test_authenticated_user_can_create_recipe(
    user_client, user, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    tags = create_tags()
    ingredients = create_ingredients()
    data = recipe_payload(tags[:2], ingredients[:2], name='Fresh oatmeal')

    response = create_single_recipe(user_client, data)

    assert response.json()['name'] == 'Fresh oatmeal'
    assert response.json()['author']['id'] == user.id
    assert len(response.json()['tags']) == 2
    assert len(response.json()['ingredients']) == 2


@pytest.mark.django_db
def test_recipe_requires_tags_and_ingredients(user_client):
    data = recipe_payload([], [])

    response = user_client.post(RECIPES_URL, data=data, format='json')

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'tags' in response.json()
    assert 'ingredients' in response.json()


@pytest.mark.django_db
def test_only_recipe_author_can_update_recipe(user, admin_client):
    recipe = create_recipe(user)

    response = admin_client.patch(
        f'{RECIPES_URL}{recipe.id}/',
        data={'name': 'Unauthorized update'},
        format='json',
    )

    assert response.status_code == HTTPStatus.FORBIDDEN