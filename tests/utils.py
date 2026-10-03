from base64 import b64encode
from http import HTTPStatus
from io import BytesIO

from PIL import Image

invalid_data_for_username_and_email_fields = [
    (
        {
            'email': ('a' * 244) + '@foodgram.fake',
            'username': 'valid-username'
        },
        'email length'
    ),
    (
        {
            'email': 'valid-email@foodgram.fake',
            'username': 'a' * 151
        },
        'username length'
    ),
    (
        {
            'email': 'valid-email@foodgram.fake',
            'username': '|-|aTa|_|_|a'
        },
        'username characters'
    ),
]

invalid_data_for_user_patch_and_creation = [
    (
        {
            **data,
            'first_name': 'Valid',
            'last_name': 'Smith',
            'password': 'test-password-123'
        },
        reason
    )
    for data, reason in invalid_data_for_username_and_email_fields
]
invalid_data_for_user_patch_and_creation.extend([
    (
        {
            'email': 'valid-email@foodgram.fake',
            'username': 'validname',
            'first_name': 'a' * 151,
            'last_name': 'Smith',
            'password': 'test-password-123'
        },
        'first_name length'
    ),
    (
        {
            'email': 'valid-email@foodgram.fake',
            'username': 'validname',
            'first_name': 'Valid',
            'last_name': 'a' * 151,
            'password': 'test-password-123'
        },
        'last_name length'
    ),
])


def check_pagination(url, response_data, expected_count, post_data=None):
    expected_keys = ('count', 'next', 'previous', 'results')
    for key in expected_keys:
        assert key in response_data, (
            f'GET `{url}` should return paginated data with `{key}`.'
        )
    assert response_data['count'] == expected_count, (
        f'GET `{url}` returned an unexpected count.'
    )
    assert isinstance(response_data['results'], list), (
        f'GET `{url}` should return a list in `results`.'
    )
    assert len(response_data['results']) == expected_count, (
        f'GET `{url}` returned an unexpected number of results.'
    )
    if post_data is not None:
        assert post_data in response_data['results'], (
            f'GET `{url}` did not return the expected object.'
        )


def create_tags():
    from recipes.models import Tag

    tag_data = (
        ('Breakfast', 'breakfast'),
        ('Lunch', 'lunch'),
        ('Dinner', 'dinner'),
    )
    return [
        Tag.objects.get_or_create(name=name, slug=slug)[0]
        for name, slug in tag_data
    ]


def create_ingredients():
    from recipes.models import Ingredient

    ingredient_data = (
        ('Oats', 'g'),
        ('Milk', 'ml'),
        ('Salt', 'g'),
    )
    return [
        Ingredient.objects.get_or_create(
            name=name,
            measurement_unit=measurement_unit
        )[0]
        for name, measurement_unit in ingredient_data
    ]


def sample_image_data_uri():
    image = Image.new('RGB', (1, 1), color='white')
    image_file = BytesIO()
    image.save(image_file, format='PNG')
    encoded_image = b64encode(image_file.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded_image}'


def recipe_payload(tags, ingredients, name='Test recipe'):
    return {
        'name': name,
        'text': 'Test recipe instructions',
        'image': sample_image_data_uri(),
        'cooking_time': 30,
        'tags': [tag.id for tag in tags],
        'ingredients': [
            {'id': ingredient.id, 'amount': 100}
            for ingredient in ingredients
        ],
    }


def create_recipe(author, tags=None, ingredients=None, name='Test recipe'):
    from recipes.models import Recipe, RecipeIngredient

    tags = tags or create_tags()[:1]
    ingredients = ingredients or create_ingredients()[:1]
    recipe = Recipe.objects.create(
        author=author,
        text='Test recipe instructions',
        name=name,
        image='recipes/images/test.png',
        cooking_time=30,
    )
    recipe.tags.set(tags)
    RecipeIngredient.objects.bulk_create([
        RecipeIngredient(recipe=recipe, ingredient=ingredient, amount=100)
        for ingredient in ingredients
    ])
    return recipe


def create_recipes(author, tags=None, ingredients=None):
    tags = tags or create_tags()
    ingredients = ingredients or create_ingredients()
    return [
        create_recipe(
            author,
            tags=[tags[0]],
            ingredients=ingredients[:2],
            name='Oatmeal',
        ),
        create_recipe(
            author,
            tags=[tags[-1]],
            ingredients=ingredients[1:],
            name='Milk porridge',
        ),
    ]


def create_single_recipe(client, data):
    response = client.post('/api/recipes/', data=data, format='json')
    assert response.status_code == HTTPStatus.CREATED, (
        'A valid authenticated POST to `/api/recipes/` should return 201.'
    )
    return response


def add_recipe_to_favorites(user, recipe):
    user.favorites.add(recipe)
    return recipe


def create_shopping_cart_item(user, recipe):
    from recipes.models import ShoppingCart

    return ShoppingCart.objects.get_or_create(user=user, recipe=recipe)[0]
