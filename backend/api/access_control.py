import unicodedata


ROLE_GERENTE = 'Gerente'
ROLE_ADMINISTRADOR = 'Administrador'
ROLE_RECEPCAO = 'Recepcao'
ROLE_COMERCIAL = 'Comercial'
ROLE_CONSUMO = 'Consumo'
ROLE_LAVANDERIA = 'Lavanderia'

FULL_ACCESS_ROLES = (ROLE_GERENTE, ROLE_ADMINISTRADOR)

RECEPCAO_ROLES = (ROLE_RECEPCAO,)
RESERVAS_ROLES = (ROLE_RECEPCAO, ROLE_COMERCIAL)
RESERVAS_READ_ROLES = (ROLE_RECEPCAO, ROLE_COMERCIAL)
RESERVA_SUPPORT_READ_ROLES = (ROLE_RECEPCAO, ROLE_COMERCIAL)
HOSPEDES_ROLES = (ROLE_RECEPCAO, ROLE_COMERCIAL)
CONSUMO_ROLES = (ROLE_CONSUMO,)
LAVANDERIA_ROLES = (ROLE_LAVANDERIA,)
CONSUMO_CONTA_READ_ROLES = (ROLE_CONSUMO, ROLE_LAVANDERIA)


ROLE_ALIASES = {
    'admin': ROLE_ADMINISTRADOR,
    'administrador': ROLE_ADMINISTRADOR,
    'gerente': ROLE_GERENTE,
    'recepcao': ROLE_RECEPCAO,
    'recepcionista': ROLE_RECEPCAO,
    'comercial': ROLE_COMERCIAL,
    'consumo': ROLE_CONSUMO,
    'atendente consumo': ROLE_CONSUMO,
    'lavanderia': ROLE_LAVANDERIA,
    'gestao': ROLE_COMERCIAL,
    'gestor': ROLE_COMERCIAL,
}


ROLE_PERMISSIONS = {
    ROLE_GERENTE: [
        'auth.perfil',
        'gestao.read',
        'reservas.manage',
        'hospedes.manage',
        'quartos.manage',
        'barcos.manage',
        'consumo.catalog.manage',
        'consumo.operacao',
        'lavanderia.operacao',
        'contas.close',
    ],
    ROLE_ADMINISTRADOR: [
        'auth.perfil',
        'gestao.read',
        'reservas.manage',
        'hospedes.manage',
        'quartos.manage',
        'barcos.manage',
        'consumo.catalog.manage',
        'consumo.operacao',
        'lavanderia.operacao',
        'contas.close',
    ],
    ROLE_RECEPCAO: [
        'auth.perfil',
        'reservas.manage',
        'hospedes.manage',
        'reservas.checkin',
    ],
    ROLE_COMERCIAL: [
        'auth.perfil',
        'reservas.manage',
        'hospedes.manage',
    ],
    ROLE_CONSUMO: [
        'auth.perfil',
        'reservas.open.read',
        'consumo.operacao',
        'contas.read',
        'contas.close',
    ],
    ROLE_LAVANDERIA: [
        'auth.perfil',
        'reservas.open.read',
        'contas.read',
        'lavanderia.operacao',
    ],
}


def normalize_role(role):
    if not role:
        return ''

    without_accents = unicodedata.normalize('NFKD', str(role))
    ascii_role = ''.join(char for char in without_accents if not unicodedata.combining(char))
    return ' '.join(ascii_role.strip().lower().split())


def canonical_role(role):
    normalized = normalize_role(role)
    return ROLE_ALIASES.get(normalized, str(role).strip() if role else '')


def role_has_full_access(role):
    normalized = normalize_role(canonical_role(role))
    return normalized in {normalize_role(item) for item in FULL_ACCESS_ROLES}


def role_is_allowed(role, allowed_roles=None):
    if not allowed_roles:
        return True

    if role_has_full_access(role):
        return True

    normalized_role = normalize_role(canonical_role(role))
    normalized_allowed = {normalize_role(canonical_role(item)) for item in allowed_roles}
    return normalized_role in normalized_allowed


def permissions_for_role(role):
    if role_has_full_access(role):
        return ROLE_PERMISSIONS[ROLE_GERENTE]

    return ROLE_PERMISSIONS.get(canonical_role(role), ['auth.perfil'])
