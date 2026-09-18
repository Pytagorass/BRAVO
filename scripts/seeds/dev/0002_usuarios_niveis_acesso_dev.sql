-- ===================================================================
-- BRAVO - Usuarios de desenvolvimento por nivel de acesso
--
-- Senha padrao de todos os usuarios:
--   123456
--
-- Nao use este seed em producao.
-- ===================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_usuario_enum') THEN
        ALTER TYPE tipo_usuario_enum ADD VALUE IF NOT EXISTS 'Administrador';
        ALTER TYPE tipo_usuario_enum ADD VALUE IF NOT EXISTS 'Recepcao';
        ALTER TYPE tipo_usuario_enum ADD VALUE IF NOT EXISTS 'Comercial';
        ALTER TYPE tipo_usuario_enum ADD VALUE IF NOT EXISTS 'Consumo';
        ALTER TYPE tipo_usuario_enum ADD VALUE IF NOT EXISTS 'Lavanderia';
    END IF;
END
$$;

BEGIN;

INSERT INTO usuario (
    nome_usuario,
    email_usuario,
    senha,
    tipo_usuario,
    ativo,
    is_superuser
)
VALUES
    (
        'Gerente',
        'gerente@aguapei.local',
        'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
        'Gerente',
        'Ativo',
        TRUE
    ),
    (
        'Administrador',
        'administrador@aguapei.local',
        'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
        'Administrador',
        'Ativo',
        TRUE
    ),
    (
        'Recepcao',
        'recepcao@aguapei.local',
        'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
        'Recepcao',
        'Ativo',
        FALSE
    ),
    (
        'Consumo',
        'consumo@aguapei.local',
        'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
        'Consumo',
        'Ativo',
        FALSE
    ),
    (
        'Lavanderia',
        'lavanderia@aguapei.local',
        'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
        'Lavanderia',
        'Ativo',
        FALSE
    ),
    (
        'Comercial',
        'comercial@aguapei.local',
        'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
        'Comercial',
        'Ativo',
        FALSE
    )
ON CONFLICT (email_usuario) DO UPDATE
SET
    nome_usuario = EXCLUDED.nome_usuario,
    senha = EXCLUDED.senha,
    tipo_usuario = EXCLUDED.tipo_usuario,
    ativo = EXCLUDED.ativo,
    is_superuser = EXCLUDED.is_superuser;

UPDATE usuario
SET
    nome_usuario = 'Comercial',
    email_usuario = 'comercial@aguapei.local',
    tipo_usuario = 'Comercial',
    ativo = 'Ativo',
    is_superuser = FALSE
WHERE
    email_usuario = 'gestao@aguapei.local'
    AND NOT EXISTS (
        SELECT 1
        FROM usuario
        WHERE email_usuario = 'comercial@aguapei.local'
    );

UPDATE usuario
SET
    nome_usuario = 'Comercial',
    tipo_usuario = 'Comercial',
    ativo = 'Inativo',
    is_superuser = FALSE
WHERE email_usuario = 'gestao@aguapei.local';

COMMIT;
