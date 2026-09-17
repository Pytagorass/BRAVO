-- ===================================================================
-- BRAVO - Seed de usuario administrador para desenvolvimento local
--
-- Login:
--   Email: admin@aguapei.local
--   Senha: 123456
--
-- A senha usa o prefixo legacy_bcrypt para ser validada pelo hasher
-- api.hashers.LegacyBCryptPasswordHasher.
--
-- Nao use este seed em producao.
-- ===================================================================

BEGIN;

INSERT INTO usuario (
    nome_usuario,
    email_usuario,
    senha,
    tipo_usuario,
    ativo
)
VALUES (
    'Administrador',
    'admin@aguapei.local',
    'legacy_bcrypt$$2b$12$xwvkIIiHygHssiyvSAsLy..D9fI.0j8I4xtLHpq16WSp.K6PZSHM.',
    'Gerente',
    'Ativo'
)
ON CONFLICT (email_usuario) DO UPDATE
SET
    nome_usuario = EXCLUDED.nome_usuario,
    senha = EXCLUDED.senha,
    tipo_usuario = EXCLUDED.tipo_usuario,
    ativo = EXCLUDED.ativo;

COMMIT;
