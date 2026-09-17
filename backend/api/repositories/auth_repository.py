from django.contrib.auth import get_user_model


Usuario = get_user_model()


def buscar_usuario_ativo_por_email(email):
    return (
        Usuario.objects.only(
            'id_usuario',
            'nome_usuario',
            'email_usuario',
            'tipo_usuario',
            'password',
        )
        .filter(email_usuario=email, ativo='Ativo')
        .order_by('id_usuario')
        .first()
    )


def buscar_usuario_ativo_por_id(usuario_id):
    return (
        Usuario.objects.only(
            'id_usuario',
            'nome_usuario',
            'email_usuario',
            'tipo_usuario',
        )
        .filter(pk=usuario_id, ativo='Ativo')
        .first()
    )
