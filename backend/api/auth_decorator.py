import jwt
from django.conf import settings
from django.http import JsonResponse
from functools import wraps
# A LINHA 'from .models import usuario' FOI REMOVIDA

def token_required(view_func):
    """
    Decorador que verifica se um JWT válido foi enviado no
    cabeçalho 'Authorization'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        
        # 1. Pega o cabeçalho 'Authorization'
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return JsonResponse({'erro': 'Token de autenticação não fornecido'}, status=401)

        # 2. Tenta dividir o cabeçalho (ex: "Bearer <token>")
        try:
            token_type, token = auth_header.split(' ')
            if token_type.lower() != 'bearer':
                raise ValueError("Tipo de token inválido")
        except ValueError:
            return JsonResponse({'erro': 'Cabeçalho de autorização mal formatado'}, status=401)

        # 3. Tenta decodificar o token
        try:
            # Usa a mesma SECRET_KEY do Django para decodificar
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # 4. Validação (Pega o ID do usuário de dentro do token)
            user_id = payload.get('id_usuario')
            if not user_id:
                raise jwt.InvalidTokenError("Payload do token inválido")

            # Adiciona o payload decodificado (info do usuário)
            # ao objeto 'request' para que a view possa usá-lo
            request.user_token_payload = payload

        except jwt.ExpiredSignatureError:
            return JsonResponse({'erro': 'Token expirado. Faça login novamente.'}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'erro': f'Token inválido: {str(e)}'}, status=401)
        except Exception as e:
            return JsonResponse({'erro': f'Erro de autenticação: {str(e)}'}, status=500)

        # 5. Se tudo deu certo, executa a view original
        return view_func(request, *args, **kwargs)

    return _wrapped_view