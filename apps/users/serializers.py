from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

from apps.users.utils import generate_temp_password

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'must_change_password')


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'is_active', 'first_name', 'last_name', 'phone')


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name', 'phone')

    def create(self, validated_data):
        temp = generate_temp_password()
        user = User(**validated_data)
        user.set_password(temp)
        user.must_change_password = True
        user.is_active = True
        user.save()
        self._temporary_password = temp
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'is_active', 'first_name', 'last_name', 'phone', 'must_change_password')

    def update(self, instance, validated_data):
        # Prevent username changes
        if 'username' in validated_data and validated_data['username'] != instance.username:
            raise serializers.ValidationError({'username': 'username cannot be changed once set'})
        return super().update(instance, validated_data)


class TokenObtainPairSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs.get('username'), password=attrs.get('password'))
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        return {'user': user}


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password incorrect')
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.must_change_password = False
        user.save()
        return user
