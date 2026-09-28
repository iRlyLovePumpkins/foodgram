from django.shortcuts import get_object_or_404, redirect
from recipes.models import Recipe

def encode_pk(pk):
    return hex(pk)[2:]

def decode_pk(code):
    try:
        return int(code, 16)
    except ValueError:
        return None

def recipe_redirect_view(request, short_code):
    recipe_id = decode_pk(short_code)
    recipe = get_object_or_404(Recipe, id=recipe_id)
    return redirect(f'/recipes/{recipe.id}')