import serpy

from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from ecommerce.utilities.serializer_mixins import BaseModelDeserializer, LocalDateTimeField, BaseSerializer, \
    BaseDeserializer
from users.models import User, PasswordResetToken

class BaseUserSerializer(BaseSerializer):
    email = serpy.StrField(required=False)
    activation_status = serpy.StrField(required=False)


class WebBasicUserSerializer(BaseSerializer):
    id = serpy.IntField()
    username = serpy.StrField()
    first_name = serpy.StrField(required=False)
    last_name = serpy.StrField(required=False)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['full_name'] = user.full_name
        return token


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class CreateBasicUserDeserializer(BaseModelDeserializer):
    """
    Used to create basic user
    """
    password = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ('email', )

    def validate(self, attrs):
        dummy_username = f"{attrs.get('first_name', '') + attrs.get('last_name', '')}_{get_random_string(4)}"
        attrs['username'] = dummy_username.lower()
        if User.objects.filter(email=attrs.get('email')).exists():
            raise ValidationError({"error": "Email already exist"})

        return attrs

    def create(self, validated_data):
        user = auth.get_user_model().objects.create(**validated_data)
        user.activation_status = User.STATUS_INVITED
        user.save()
        return user


class UserDeserializer(BaseModelDeserializer):
    """
    update user details
    """

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def update(self, instance, validated_data):

        return super().update(instance, validated_data)


class ActivateUserDeserializer(BaseModelDeserializer):
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

    def update(self, instance: User, validated_data):
        validated_keys = validated_data.keys()
        for key in self.Meta.fields:
            if key not in validated_keys:
                raise ValidationError({key: "this field is required"})

        instance.email = validated_data.get('email')
        instance.username = validated_data.get('username')
        instance.first_name = validated_data.get('first_name')
        instance.last_name = validated_data.get('last_name')
        instance.date_of_birth = validated_data.get('date_of_birth')
        instance.set_password(validated_data.get('password'))
        instance.is_active = True
        instance.activation_status = User.STATUS_ACCEPTED
        instance.date_joined = timezone.now()
        instance.save()
        return instance

    @staticmethod
    def validate_password(password):
        validate_password(password)
        return password


class UserSerializer(WebBasicUserSerializer):
    email = serpy.StrField(required=False)
    date_of_birth = serpy.StrField(required=False)
    # Status
    activation_status = serpy.StrField()
    is_active = serpy.BoolField()
    is_staff = serpy.BoolField()
    is_superuser = serpy.BoolField()
    date_joined = LocalDateTimeField()
    updated_at = LocalDateTimeField()
    created_at = LocalDateTimeField()


class BaseGroupSerializer(BaseSerializer):
    id = serpy.StrField()
    name = serpy.StrField()


class UsersSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name')


class UserUpdateDeserializer(BaseModelDeserializer):
    class Meta:
        model = User
        fields = '__all__'

    def update(self, instance: User, validated_data):
        validated_keys = validated_data.keys()
        for key in self.Meta.fields:
            if key not in validated_keys:
                raise ValidationError({key: "this field is required"})

        instance.email = validated_data.get('email')
        instance.username = validated_data.get('username')
        instance.first_name = validated_data.get('first_name')
        instance.last_name = validated_data.get('last_name')
        instance.date_of_birth = validated_data.get('date_of_birth')
        instance.set_password(validated_data.get('password'))
        instance.is_active = True
        instance.save()
        return instance

    @staticmethod
    def validate_password(password):
        validate_password(password)
        return password


class WebResetPasswordDeserializer(BaseDeserializer):
    """
        Serializer for password reset endpoint after forget password.
    """
    password = serializers.CharField()
    token = serializers.CharField()

    class Meta:
        model = User
        fields = ["password", "token"]

    @staticmethod
    def validate_token(value):
        try:
            token = PasswordResetToken.objects.get(token=value)
            if token.is_expired():
                token.delete()
                raise ValidationError("Token is expired")
            return token

        except PasswordResetToken.DoesNotExist:
            raise ValidationError("PasswordResetToken does not exist.")

    @staticmethod
    def validate_password(value):
        # Let django validate the new password, it raises exception if does not pass the check.
        validate_password(value)

        return value

    def create(self, validated_data):
        password = validated_data["password"]
        token = validated_data["token"]

        user = token.user
        user.set_password(password)
        user.save()

        token.delete()

        return user


class ChangePasswordDeserializer(BaseDeserializer):
    model = User
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
