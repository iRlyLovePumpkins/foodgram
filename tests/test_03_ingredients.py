from http import HTTPStatus

import pytest

from tests.utils import create_ingredients

INGREDIENTS_URL = '/api/ingredients/'


@pytest.mark.django_db
def test_ingredients_are_public_and_searchable(client, admin_client):
    ingredients = create_ingredients()

    response = client.get(INGREDIENTS_URL)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(ingredients)
    assert {'id', 'name', 'measurement_unit'} <= set(data[0])

    search_response = client.get(f'{INGREDIENTS_URL}?name=oa')
    assert search_response.status_code == HTTPStatus.OK
    assert [item['name'] for item in search_response.json()] == ['Oats']

    detail_response = client.get(f'{INGREDIENTS_URL}{ingredients[0].id}/')
    assert detail_response.status_code == HTTPStatus.OK
    assert detail_response.json()['measurement_unit'] == 'g'

    post_response = admin_client.post(
        INGREDIENTS_URL,
        data={'name': 'Flour', 'measurement_unit': 'g'},
    )
    assert post_response.status_code == HTTPStatus.METHOD_NOT_ALLOWED