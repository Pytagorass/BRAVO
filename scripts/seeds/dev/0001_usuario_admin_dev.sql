-- ===================================================================
-- BRAVO - Seed de usuario administrador para desenvolvimento local
--
-- Login:
--   Email: admin@aguapei.local
--   Senha: 123456
--
-- A senha usa o hash padrao do Django.
--
-- Nao use este seed em producao.
-- ===================================================================

BEGIN;

INSERT INTO usuario (
    nome_usuario,
    email_usuario,
    senha,
    tipo_usuario,
    ativo,
    is_superuser
)
VALUES (
    'Administrador',
    'admin@aguapei.local',
    'pbkdf2_sha256$1000000$Biugj4pdHp88FwylklrmpJ$cybZdT+Y/jMIDQpes86aMmbVItnXJNUT7TyUQRDVMBQ=',
    'Gerente',
    'Ativo',
    TRUE
)
ON CONFLICT (email_usuario) DO UPDATE
SET
    nome_usuario = EXCLUDED.nome_usuario,
    senha = EXCLUDED.senha,
    tipo_usuario = EXCLUDED.tipo_usuario,
    ativo = EXCLUDED.ativo,
    is_superuser = EXCLUDED.is_superuser;

COMMIT;
