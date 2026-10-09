from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Count, Exists, OuterRef, Sum, Value
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from foodgram_backend.settings import ALLOWED_METHODS
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)

from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .utils import encode_pk

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
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
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    )
    filterset_class = RecipeFilter
    search_fields = ('name',)
    ordering_fields = ('id', 'name')
    permission_classes = [
        IsAuthorOrReadOnly,
        permissions.IsAuthenticatedOrReadOnly
    ]
    http_method_names = ALLOWED_METHODS

    def _handle_recipe_action(self, request, model, msgs):
        recipe = self.get_object()
        user = request.user

        if hasattr(model, 'objects'):
            item_filter = model.objects.filter(user=user, recipe=recipe)
            exists = item_filter.exists()
        else:
            exists = model.filter(pk=recipe.pk).exists()

        if request.method == 'POST':
            if exists:
                return Response(
                    {'errors': msgs['already_exists']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if hasattr(model, 'objects'):
                model.objects.create(user=user, recipe=recipe)
            else:
                model.add(recipe)

            serializer = RecipeShortSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not exists:
            return Response(
                {'errors': msgs['not_found']},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(model, 'objects'):
            item_filter.delete()
        else:
            model.remove(recipe)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def filter_by_param(self, qs, param_name):
        """
        Вспомогательный метод для фильтрации по параметрам
        (is_favorited, is_in_shopping_cart).
        """
        param = self.request.query_params.get(param_name)
        if param is not None:
            if not self.request.user.is_authenticated:
                return qs.none()
            is_true = str(param).lower() in ('1', 'true')
            return qs.filter(**{param_name: is_true})
        return qs

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

        response = HttpResponse(
            file_content,
            content_type='text/plain; charset=utf-8'
        )
        filename = f"{user.username}_shopping_list.txt"
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"'
        )
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_recipe_action(
            request,
            ShoppingCart,
            {
                'already_exists': 'Рецепт уже добавлен в список покупок.',
                'not_found': 'Рецепт не найден в списке покупок.'
            }
        )

    @action(
        detail=True,
        permission_classes=[permissions.IsAuthenticated],
        methods=['post', 'delete'],
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        return self._handle_recipe_action(
            request,
            request.user.favorites,
            {
                'already_exists': 'Рецепт уже есть в избранном.',
                'not_found': 'Рецепт не найден в избранном.'
            }
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    user.favorites.filter(pk=OuterRef('pk'))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user, recipe=OuterRef('pk')
                    )
                )
            )
        else:
            queryset = queryset.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField())
            )

        queryset = self.filter_by_param(queryset, 'is_in_shopping_cart')
        queryset = self.filter_by_param(queryset, 'is_favorited')

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    lookup_field = 'id'
    permission_classes = (AllowAny, )
    filter_backends = (filters.SearchFilter,)
    search_fields = ('username', 'email')
    ordering_fields = ('id', 'username')
    http_method_names = ALLOWED_METHODS

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        self.request.user.set_password(
            serializer.validated_data['new_password']
        )
        self.request.user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get', 'patch'),
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        serializer = self.get_serializer(
            user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=('put', 'delete'),
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = self.get_serializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'avatar': user.avatar.url if user.avatar else None},
                status=status.HTTP_200_OK
            )

        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        authors = user.subscriptions.all().annotate(
            recipes_count=Count('recipes')
        )
        paginated_authors = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            paginated_authors,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = self.get_object()
        is_subscribed = author.subscribers.filter(pk=user.pk).exists()

        if request.method == 'POST':
            if author == user:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if is_subscribed:
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.subscriptions.add(author)
            author = User.objects.annotate(
                recipes_count=Count('recipes')
            ).get(pk=author.pk)

            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not is_subscribed:
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.subscriptions.remove(author)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()

        if user.is_authenticated:
            return queryset.annotate(
                is_subscribed=Exists(
                    user.subscriptions.filter(pk=OuterRef('pk'))
                )
            )

        return queryset.annotate(
            is_subscribed=Value(False, output_field=BooleanField())
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
