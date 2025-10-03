# api_core/authentication.py

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth

# Importa a instância 'db' apenas para garantir que o Firebase foi inicializado
from .firebase_config import db

# Classe simples para representar um usuário autenticado via Firebase
class FirebaseUser:
    def __init__(self, token):
        self.uid = token.get('uid')
        self.email = token.get('email')

    # A propriedade que a permissão 'IsAuthenticated' procura
    @property
    def is_authenticated(self):
        return True

class FirebaseAuthentication(BaseAuthentication):
    """
    Classe de autenticação para o Django REST Framework que valida
    Tokens ID do Firebase enviados no cabeçalho 'Authorization'.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) == 1 or parts[0].lower() != 'bearer':
            return None

        id_token = parts[1]

        try:
            decoded_token = auth.verify_id_token(id_token)
        except Exception as e:
            raise AuthenticationFailed(f'Token inválido: {e}')

        if not decoded_token:
            raise AuthenticationFailed('Token inválido.')

        # ===== A CORREÇÃO ESTÁ AQUI =====
        # Agora retornamos uma instância do nosso FirebaseUser e o token
        user = FirebaseUser(decoded_token)
        return (user, decoded_token)