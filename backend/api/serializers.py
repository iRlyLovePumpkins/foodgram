from django.contrib.auth import authenticate, get_user_model
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Ingredient, Recipe, RecipeIngredient, ShoppingCart,
                            Tag)
from rest_framework import serializers

User = get_user_model()


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


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes',
            'recipes_count', 'avatar'
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

        serializer = RecipeShortSerializer(
            recipes,
            many=True,
            context={'request': request}
        )
        return serializer.data


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
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

    def get_is_subscribed(self, obj):
        annotated_value = getattr(obj, 'is_subscribed', None)
        if annotated_value is not None:
            return annotated_value

        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False

        return request.user.subscriptions.filter(pk=obj.pk).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredient',
        many=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField(required=True)
    author = UserSerializer(read_only=True)
    is_favorited = serializers.BooleanField(
        read_only=True, default=False
    )
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False
    )

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
            'text',
            'cooking_time',
        )

    def validate(self, data):
        if self.instance:
            if 'recipe_ingredient' not in data and 'ingredients' not in data:
                raise serializers.ValidationError(
                    {'ingredients':
                     'Нужен хотя бы один ингредиент для рецепта'}
                )
            if 'tags' not in data:
                raise serializers.ValidationError(
                    {'tags': 'Нужен хотя бы один тег для рецепта'}
                )
        return data

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Нужен хотя бы один ингредиент для рецепта."
            )
        ingredient_ids = [item['ingredient'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                "Нужен хотя бы один тег для рецепта."
            )
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Тэги не должны повторяться."
            )
        return value

    def validate_cooking_time(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Время приготовления должно быть больше нуля."
            )
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError("Картинка обязательна")
        return value

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['tags'] = TagSerializer(instance.tags.all(), many=True).data
        response['ingredients'] = RecipeIngredientSerializer(
            instance.recipe_ingredient.all(),
            many=True
        ).data
        return response

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredient', [])
        tags_data = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data.get('ingredient'),
                amount=ingredient_data.get('amount')
            )

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredient', None)
        tags_data = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.recipe_ingredient.all().delete()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient_data.get('ingredient'),
                    amount=ingredient_data.get('amount')
                )
        return instance


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe')


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
