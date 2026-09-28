from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Exists, OuterRef, Value, BooleanField, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from api.serializers import (
    TagSerializer,
    RecipeSerializer,
    IngredientSerializer,
    RecipeShortSerializer
)
from .models import (
    Tag,
    Recipe,
    Ingredient,
)
from .utils import encode_pk, decode_pk
from .permissions import IsAuthorOrReadOnly
from .models import RecipeIngredient, ShoppingCart


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'recipe_ingredient__ingredient'
    ).all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly]

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_code = encode_pk(recipe.pk)
        short_url = request.build_absolute_uri(f'/s/{short_code}/')
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)

    @action(
            detail=False,
            methods=['get'],
            url_path='download_shopping_cart',
        )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shopping_cart__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        shopping_list = ['Список покупок:\n']
        for item in ingredients:
            name = item['ingredient__name']
            measurement = item['ingredient__measurement_unit']
            amount = item['total_amount']
            shopping_list.append(f'- {name}: {amount} {measurement}\n')

        file_content = ''.join(shopping_list)

        response = HttpResponse(file_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(
            detail=True,
            methods=['post', 'delete'],
            url_path='shopping_cart'
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if cart_item.exists():
                return Response(
                    {'errors': 'Рецепт уже добавлен в список покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not cart_item.exists():
                return Response(
                    {'errors': 'Рецепт не найден в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        is_favorite = user.favorites.filter(pk=recipe.pk).exists()

        if request.method == 'POST':
            if is_favorite:
                return Response(
                    {'errors': 'Рецепт уже есть в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.favorites.add(recipe)
            serializer = RecipeShortSerializer(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not is_favorite:
                return Response(
                    {'errors': 'Рецепт не найден в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.favorites.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    user.favorites.filter(pk=OuterRef('pk'))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user, recipe=OuterRef('pk'))
                )
            )
        else:
            queryset = queryset.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField())
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
