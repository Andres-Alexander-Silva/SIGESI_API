from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.validators import RegexValidator
from apps.sigesi.models import User

class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            RegexValidator(
                regex=r'^[\w\.-]+@ufps\.edu\.co$',
                message='El correo debe pertenecer al dominio @ufps.edu.co.'
            ),
            UniqueValidator(
                queryset=User.objects.all(),
                message='Ya existe un usuario registrado con este correo electrónico.'
            )
        ]
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'cedula']
        extra_kwargs = {
            'password': {'write_only': True}
        }
        
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
