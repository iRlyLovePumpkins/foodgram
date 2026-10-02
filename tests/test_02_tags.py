from http import HTTPStatus

import pytest

from tests.utils import create_tags


TAGS_URL = '/api/tags/'


@pytest.mark.django_db
def test_tags_are_public_and_read_only(client, admin_client):
    tags = create_tags()

    response = client.get(TAGS_URL)

    assert response.status_code == HTTPStatus.OK
    tag_data = response.json()
    assert isinstance(tag_data, list)
    assert len(tag_data) == len(tags)
    assert {'id', 'name', 'slug'} <= set(tag_data[0])

    detail_response = client.get(f'{TAGS_URL}{tags[0].id}/')
    assert detail_response.status_code == HTTPStatus.OK
    assert detail_response.json()['slug'] == tags[0].slug

    post_response = admin_client.post(
        TAGS_URL, data={'name': 'Snack', 'slug': 'snack'}
    )
    assert post_response.status_code == HTTPStatus.METHOD_NOT_ALLOWED