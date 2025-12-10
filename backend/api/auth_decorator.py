"""
Módulo responsável por centralizar o decorador de autenticação JWT.
Todas as views protegidas o utilizam para garantir que o token gerado
em `login_view` (consumido pelo React) seja validado antes da execução.
"""

import jwt
from django.conf import settings
from django.http import JsonResponse
from functools import wraps


def token_required(view_func):
    """
    Decorador utilizado nas views protegidas (reservas, hóspedes, BI).

    Parâmetros:
        view_func (callable): view original que requer autenticação.

    Retorno:
        callable: função embrulhada que executa a validação antes de
        chamar a view real. Em caso de falha retorna JsonResponse 401/500.

    Fluxo resumido:
        1. Lê o cabeçalho Authorization enviado pelo axios (Bearer token).
        2. Valida o prefixo e extrai o JWT.
        3. Decodifica com SECRET_KEY e verifica se `id_usuario` existe.
        4. Anexa o payload no request (usado para auditoria nas views).
        5. Em caso de sucesso, chama a view originalmente decorada.

    Relação com o front-end:
        O `apiClient` injeta `Authorization: Bearer <token>` em todas as
        requisições após o login. Este decorador faz o gatekeeper dessas
        rotas, devolvendo 401 para que o React trate e redirecione para o
        `/login` quando necessário.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Recupera o header Authorization enviado pelo axios interceptor.
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return JsonResponse({'erro': 'Token de autenticação não fornecido'}, status=401)

        # 2. Garante o formato "Bearer <token>".
        try:
            token_type, token = auth_header.split(' ')
            if token_type.lower() != 'bearer':
                raise ValueError("Tipo de token inválido")
        except ValueError:
            return JsonResponse({'erro': 'Cabeçalho de autorização mal formatado'}, status=401)

        # 3. Decodifica o JWT usando a mesma SECRET_KEY do projeto.
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            # 4. Sem `id_usuario` o token é considerado inválido (payload adulterado).
            user_id = payload.get('id_usuario')
            if not user_id:
                raise jwt.InvalidTokenError("Payload do token inválido")

            # Deixa os dados disponíveis para as views (ex.: logs de usuário).
            request.user_token_payload = payload

        except jwt.ExpiredSignatureError:
            return JsonResponse({'erro': 'Token expirado. Faça login novamente.'}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'erro': f'Token inválido: {str(e)}'}, status=401)
        except Exception as e:
            return JsonResponse({'erro': f'Erro de autenticação: {str(e)}'}, status=500)

        # 5. Se tudo deu certo, encaminha para a view original.
        return view_func(request, *args, **kwargs)

    return _wrapped_view
