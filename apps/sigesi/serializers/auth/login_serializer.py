from rest_framework import serializers

class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class LoginResponseSerializer(serializers.Serializer):
    usuarioId = serializers.IntegerField()
    email = serializers.EmailField()
    names = serializers.CharField()
    roleCode = serializers.CharField()
    roleName = serializers.CharField()
    token = serializers.CharField()
    refreshToken = serializers.CharField(required=False)
    response = serializers.CharField()

class RefreshRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()

class RefreshResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    refreshToken = serializers.CharField()

class LogoutRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()

