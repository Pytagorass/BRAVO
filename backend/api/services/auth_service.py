import json

from django.contrib.auth import authenticate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from ..access_control import permissions_for_role
from ..repositories import auth_repository
from ..responses import error_response, success_response


def _parse_json_body(request):
    try:
        return json.loads(request.body or '{}'), None
    except json.JSONDecodeError:
        return None, error_response('JSON invalido.', 'INVALID_JSON', 400)


def _add_usuario_claims(token, usuario):
    token['id_usuario'] = usuario.id_usuario
    token['email'] = usuario.email_usuario
    token['tipo_usuario'] = usuario.tipo_usuario
    token['nome'] = usuario.nome_usuario
    return token


def _gerar_tokens(usuario):
    refresh = _add_usuario_claims(RefreshToken(), usuario)
    access = refresh.access_token
    return {
        'access': str(access),
        'refresh': str(refresh),
    }


def _usuario_payload(usuario):
    return {
        'id': usuario.id_usuario,
        'nome': usuario.nome_usuario,
        'email': usuario.email_usuario,
        'tipo': usuario.tipo_usuario,
        'permissoes': permissions_for_role(usuario.tipo_usuario),
    }


def login(request):
    try:
        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        email = data.get('email')
        senha_recebida = data.get('senha')

        if not email or not senha_recebida:
            return error_response('Email e senha sao obrigatorios', 'VALIDATION_ERROR', 400)

        usuario = authenticate(request, username=email, password=senha_recebida)
        if not usuario:
            return error_response('Credenciais invalidas ou usuario inativo', 'AUTH_FAILED', 401)

        tokens = _gerar_tokens(usuario)

        return success_response(
            {
                'token': tokens['access'],
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'usuario': _usuario_payload(usuario),
            }
        )
    except TokenError as exc:
        return error_response(f'Erro ao gerar token: {str(exc)}', 'TOKEN_ERROR', 500)
    except Exception as exc:
        return error_response(f'Erro interno: {str(exc)}', 'SERVER_ERROR', 500)


def refresh_token(request):
    try:
        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        refresh_value = data.get('refresh')
        if not refresh_value:
            return error_response('Refresh token e obrigatorio.', 'VALIDATION_ERROR', 400)

        refresh = RefreshToken(refresh_value)
        usuario_id = refresh.payload.get('id_usuario')
        if not usuario_id:
            return error_response('Refresh token invalido.', 'INVALID_TOKEN', 401)

        usuario = auth_repository.buscar_usuario_ativo_por_id(usuario_id)
        if not usuario:
            return error_response('Usuario inativo ou nao encontrado.', 'AUTH_FAILED', 401)

        access = _add_usuario_claims(refresh.access_token, usuario)

        return success_response(
            {
                'token': str(access),
                'access': str(access),
                'refresh': str(refresh),
                'usuario': _usuario_payload(usuario),
            }
        )
    except TokenError:
        return error_response('Refresh token expirado ou invalido.', 'INVALID_TOKEN', 401)
    except Exception as exc:
        return error_response(f'Erro interno: {str(exc)}', 'SERVER_ERROR', 500)
