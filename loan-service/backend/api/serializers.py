from django.contrib.auth.models import Group, User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

# ---- USER REGISTER SERIALIZER ---- #
class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Registo de novos utilizadores.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        """
        Cria um novo utilizador com os dados validados.
        """
        if User.objects.filter(username=validated_data['email']).exists():
            raise ValidationError("O email inserido já se encontra registado.")

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


# ---- USER SERIALIZER ---- #
class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para visualizar dados do utilizador.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


# ---- CUSTOM JWT TOKEN SERIALIZER ---- #
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Permite autenticação utilizando o email e adiciona campos extras ao payload do token.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Adiciona informações extras no payload
        token['email'] = user.email # vai servir com id na tabela do dynamo DB na aws com os pedidos de emprestimo
        token['first_name'] = user.first_name # este n são usados
        token['last_name'] = user.last_name

        return token

    def validate(self, attrs):
        # Sobrescreve 'username' para aceitar o email como credencial
        email = attrs.get("username")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Email e password são obrigatórios.")

        # Autentica o utilizador
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Credenciais inválidas.")

        # Substitui 'username' para o token JWT
        attrs["username"] = user.username

        return super().validate(attrs)


# ---- GROUP SERIALIZER ---- #
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']
