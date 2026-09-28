from django.contrib.auth import get_user_model
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from djoser.serializers import SetPasswordSerializer
from api.serializers import UserCreateSerializer, UserSerializer, SubscriptionSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Exists, OuterRef, Value, BooleanField, Count
from rest_framework.response import Response

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с пользователями"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'
    permission_classes = (AllowAny, )
    filter_backends = (filters.SearchFilter,)
    search_fields = ('username',)
    http_method_names = ['get', 'post', 'delete', 'put']

    @action(
        detail=False, 
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        self.request.user.set_password(serializer.validated_data['new_password'])
        self.request.user.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get', 'patch'),
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
            user = request.user
            annotated_user = self.get_queryset().filter(pk=user.pk).first() if user.is_authenticated else user
            if request.method == 'GET':
                serializer = self.get_serializer(annotated_user)
                return Response(serializer.data)

            serializer = self.get_serializer(
                user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            updated_annotated_user = self.get_queryset().filter(pk=user.pk).first() if user.is_authenticated else user
            serializer = self.get_serializer(updated_annotated_user)
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
            if 'avatar' not in request.data:
                return Response(
                    {'avatar': ['Обязательное поле.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'avatar': user.avatar.url if user.avatar else None}, status=status.HTTP_200_OK)

        if request.method == 'DELETE':
            user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
            detail=False,
            methods=['get'],
            url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        authors = user.subscriptions.all().annotate(recipes_count=Count('recipes'))
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
    def subscribe(self, request, pk=None):
        user = request.user
        author = self.get_object()
        is_subscribed = user.subscriptions.filter(pk=author.pk).exists()

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
            author = User.objects.annotate(recipes_count=Count('recipes')).get(pk=author.pk)
            serializer = SubscriptionSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
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

