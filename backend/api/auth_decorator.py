from functools import wraps

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .access_control import role_is_allowed
from .models import Usuario
from .responses import error_response


def _extract_bearer_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None, error_response('Token de autenticacao nao fornecido.', 'AUTH_TOKEN_MISSING', 401)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None, error_response('Cabecalho de autorizacao mal formatado.', 'AUTH_HEADER_INVALID', 401)

    return parts[1], None


def _get_active_usuario(usuario_id):
    return (
        Usuario.objects.only(
            'id_usuario',
            'nome_usuario',
            'email_usuario',
            'tipo_usuario',
            'ativo',
        )
        .filter(pk=usuario_id, ativo='Ativo')
        .first()
    )


def _build_request_payload(token_payload, usuario):
    payload = dict(token_payload)
    payload.update(
        {
            'id_usuario': usuario.id_usuario,
            'email': usuario.email_usuario,
            'tipo_usuario': usuario.tipo_usuario,
            'nome': usuario.nome_usuario,
        }
    )
    return payload


def _roles_for_method(request, roles, method_roles):
    if not method_roles:
        return roles

    return method_roles.get(request.method, roles)


def token_required(view_func=None, *, roles=None, method_roles=None):
    def decorator(func):
        @wraps(func)
        def _wrapped_view(request, *args, **kwargs):
            token, token_error = _extract_bearer_token(request)
            if token_error:
                return token_error

            try:
                access_token = AccessToken(token)
            except TokenError:
                return error_response('Token expirado ou invalido.', 'INVALID_TOKEN', 401)

            usuario_id = access_token.payload.get('id_usuario')
            if not usuario_id:
                return error_response('Token invalido, ID de usuario nao encontrado.', 'INVALID_TOKEN', 401)

            usuario = _get_active_usuario(usuario_id)
            if not usuario:
                return error_response('Usuario inativo ou nao encontrado.', 'AUTH_USER_INACTIVE', 401)

            allowed_roles = _roles_for_method(request, roles, method_roles)
            if not role_is_allowed(usuario.tipo_usuario, allowed_roles):
                return error_response(
                    'Usuario sem permissao para acessar este recurso.',
                    'FORBIDDEN',
                    403,
                )

            request.usuario_autenticado = usuario
            request.user_token_payload = _build_request_payload(access_token.payload, usuario)
            return func(request, *args, **kwargs)

        return _wrapped_view

    if view_func is None:
        return decorator

    return decorator(view_func)
