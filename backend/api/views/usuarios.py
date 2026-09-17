import json

from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import permissions_for_role
from ..auth_decorator import token_required
from ..models import Usuario
from ..responses import error_response, success_response


def _usuario_perfil_to_dict(usuario):
    return {
        'id_usuario': usuario.id_usuario,
        'nome_usuario': usuario.nome_usuario,
        'email_usuario': usuario.email_usuario,
        'tipo_usuario': usuario.tipo_usuario,
        'permissoes': permissions_for_role(usuario.tipo_usuario),
    }


@csrf_exempt
@token_required
@require_http_methods(["GET", "PUT"])
def usuario_perfil_view(request):
    user_id = request.user_token_payload.get('id_usuario')
    if not user_id:
        return error_response('Token invalido, ID de usuario nao encontrado.', 'INVALID_TOKEN', 401)

    if request.method == 'GET':
        try:
            usuario = Usuario.objects.get(pk=user_id)
            return success_response(_usuario_perfil_to_dict(usuario))
        except Usuario.DoesNotExist:
            return error_response('Usuario nao encontrado no banco.', 'NOT_FOUND', 404)
        except Exception as exc:
            return error_response(f'Erro no GET: {str(exc)}', 'SERVER_ERROR', 500)

    try:
        data = json.loads(request.body or '{}')
        usuario = Usuario.objects.get(pk=user_id)
        usuario.nome_usuario = data.get('nome_usuario')
        usuario.email_usuario = data.get('email_usuario')

        update_fields = ['nome_usuario', 'email_usuario']
        senha = data.get('senha')
        if senha:
            usuario.set_password(senha)
            update_fields.append('password')

        usuario.save(update_fields=update_fields)
        return success_response(None, 'PROFILE_UPDATED')
    except Usuario.DoesNotExist:
        return error_response('Usuario nao encontrado, nada atualizado.', 'NOT_FOUND', 404)
    except IntegrityError:
        return error_response('Este e-mail ja esta em uso por outra conta.', 'CONFLICT', 409)
    except Exception as exc:
        return error_response(f'Erro no PUT: {str(exc)}', 'SERVER_ERROR', 500)
