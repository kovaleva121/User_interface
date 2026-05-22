from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from users.models import User


class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор регистрации.
    Принимает password + password_confirm, валидирует совпадение,
    хеширует пароль через set_password.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = [
            'id', 'email',
            'first_name', 'last_name', 'patronymic',
            'password', 'password_confirm',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'Пароли не совпадают.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  # хеширование
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор просмотра и обновления профиля.
    Пароль не возвращается в ответе.
    """

    class Meta:
        model = User
        fields = [
            'id', 'email',
            'first_name', 'last_name', 'patronymic',
            'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'is_active', 'date_joined']


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор обновления профиля.
    Поддерживает смену пароля — через set_password, не напрямую.
    """
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = [
            'email',
            'first_name', 'last_name', 'patronymic',
            'password', 'password_confirm',
        ]

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError({'password': 'Пароли не совпадают.'})

        return attrs

    def update(self, instance, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class UserAdminSerializer(serializers.ModelSerializer):
    """
    Сериализатор для администратора — видит все поля включая is_active/is_staff.
    """

    class Meta:
        model = User
        fields = [
            'id', 'email',
            'first_name', 'last_name', 'patronymic',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']
