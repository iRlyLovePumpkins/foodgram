import base64
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.core.files.base import ContentFile
from recipes.models import (
    Tag,
    Recipe,
    Ingredient,
    RecipeIngredient,
    ShoppingCart
)
from drf_extra_fields.fields import Base64ImageField

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if data in [None, '']:
            return None
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=150
        )
    last_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=150
        )
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )
        read_only_fields = (
            'id',
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredient', 
        many=True,
        read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField(required=True)
    author = UserSerializer(read_only=True)
    description = serializers.CharField(required=False, allow_blank=True)
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'description',
            'cooking_time',
            'pub_date',
            'text'
        )


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe')


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 
            'last_name', 'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        
        limit = request.query_params.get('recipes_limit')
        if limit is not None:
            try:
                recipes = recipes[:int(limit)]
            except (ValueError, TypeError):
                pass
                
        serializer = RecipeShortSerializer(recipes, many=True, context={'request': request})
        return serializer.data


class CustomCreateTokenSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )
            if not user:
                raise serializers.ValidationError(
                    'Невозможно войти с предоставленными учетными данными.'
                )
        else:
            raise serializers.ValidationError(
                'Укажите email и пароль'
            )
        self.user = user
        attrs['user'] = user
        return attrs