# BRAVO - Barco-Hotel Aguapei

Sistema de gestao para operacao de barco-hotel, com backend em Django e frontend em React.

O projeto usa PostgreSQL como banco de dados. A estrutura do banco e versionada por migrations do Django; algumas consultas operacionais seguem em SQL manual nos repositories quando a regra exige consultas mais especificas.

## Tecnologias

- Python 3.11+
- Django
- PostgreSQL 13+
- Node.js 18+
- React

## Estrutura do Projeto

```text
BRAVO/
  backend/                  API Django
  frontend/aguapei_frontend/ Frontend React
  scripts/seeds/             Seeds separados por finalidade
  scripts/postgres/          SQL legado de referencia
  schema.sql                 Script legado de referencia
```

## Banco de Dados

O backend esta configurado em `backend/aguapei_backend/settings.py` para conectar em:

```text
Banco: Barco_Hotel
Usuario: postgres
Senha: 123
Host: localhost
Porta: 5432
```

Crie o banco no PostgreSQL com o nome `Barco_Hotel` e execute as migrations do Django.

```powershell
cd C:\Users\pytag\BRAVO\backend
python manage.py migrate
```

Se voce ja tiver um banco criado anteriormente via `schema.sql` e scripts manuais, registre a migration inicial sem recriar tabelas:

```powershell
python manage.py migrate --fake-initial
```

Os arquivos `schema.sql` e `scripts/postgres/` ficam como referencia historica e apoio para dados/seeds, mas o caminho principal de estrutura e `python manage.py migrate`.

As migrations tambem carregam os catalogos obrigatorios do sistema, como tipos de passeio, categorias de produto e lavanderia por peca.

Para desenvolvimento local, crie o usuario administrador padrao:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://postgres:123@localhost:5432/Barco_Hotel" -f "C:\Users\pytag\BRAVO\scripts\seeds\dev\0001_usuario_admin_dev.sql"
```

Dados demonstrativos ficam em `scripts/seeds/demo/` e sao opcionais.

## Login Padrao

```text
Email: admin@aguapei.local
Senha: 123456
```

## Rodando o Backend

Abra um terminal PowerShell:

```powershell
cd C:\Users\pytag\BRAVO\backend
python -m pip install -r requirements.txt
python manage.py runserver 127.0.0.1:8000
```

A API ficara disponivel em:

```text
http://127.0.0.1:8000/api
```

Para validar a configuracao do Django sem subir o servidor:

```powershell
python manage.py check
```

## Autenticacao e Acessos

O backend usa Django REST Framework + Simple JWT para emitir access token e refresh token.
O usuario autenticavel do Django e `api.Usuario`, mapeado sobre a tabela existente `usuario`.

Rotas principais:

- `POST /api/login/`: autentica e retorna `token`, `access`, `refresh` e dados do usuario.
- `POST /api/token/refresh/`: recebe `refresh` e retorna novo `access`.

O decorator de autenticacao confere se o usuario continua ativo no banco a cada requisicao protegida. Revogacao real de sessoes, auditoria de acessos e limite de tentativas ficam para a proxima camada, com tabela propria de sessoes/tentativas.
Senhas antigas em bcrypt legado sao reconhecidas temporariamente e convertidas para o hash padrao do Django no primeiro login bem-sucedido.

Niveis de acesso iniciais:

- `Gerente` ou `Administrador`: acesso total.
- `Recepcao`: reservas, hospedes, leitura operacional e fechamento de contas.
- `Consumo`: lancamentos de bebidas/lojinha e lavanderia pelo app mobile.
- `Lavanderia`: ordens e status de lavanderia.
- `Gestao`: leitura de indicadores, agenda e cadastros operacionais.

## Rodando o Frontend

Abra outro terminal PowerShell:

```powershell
cd C:\Users\pytag\BRAVO\frontend\aguapei_frontend
npm install
npm start
```

O frontend ficara disponivel em:

```text
http://localhost:3000
```

O frontend chama o backend em:

```text
http://127.0.0.1:8000/api
```

## Fluxo Basico de Uso

1. Suba o PostgreSQL.
2. Confirme que o banco `Barco_Hotel` existe.
3. Rode o backend Django na porta `8000`.
4. Rode o frontend React na porta `3000`.
5. Acesse `http://localhost:3000`.
6. Entre com o usuario administrador padrao.

## Arquivos Importantes

- `backend/aguapei_backend/settings.py`: configuracao do Django e conexao com o banco.
- `backend/api/views/`: endpoints da API organizados por modulo.
- `backend/api/services/`: regras de negocio.
- `backend/api/repositories/`: acesso ao banco, incluindo SQL manual quando necessario.
- `backend/api/migrations/`: versao oficial da estrutura do banco.
- `backend/api/urls.py`: rotas da API.
- `frontend/aguapei_frontend/src/services/api.js`: configuracao do Axios e URL do backend.
- `scripts/seeds/`: dados auxiliares separados entre fallback obrigatorio, desenvolvimento e demonstracao.
- `scripts/postgres/`: scripts legados anteriores ao fluxo oficial de migrations.
- `schema.sql`: referencia legada da estrutura inicial.

## Problemas Comuns

### Erro de conexao com o servidor no frontend

Confirme que o backend esta rodando:

```powershell
cd C:\Users\pytag\BRAVO\backend
python manage.py runserver 127.0.0.1:8000
```

### Erro de conexao com PostgreSQL

Confira se o servico do PostgreSQL esta ativo e se as credenciais em `settings.py` batem com a sua instalacao local.

No Windows:

```powershell
Get-Service *postgres*
```

### `psql` nao reconhecido

Use o caminho completo do executavel:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe"
```

### Porta 3000 ocupada

O React pode oferecer outra porta automaticamente. Se aparecer a pergunta no terminal, confirme com `Y`.

### Porta 8000 ocupada

Rode o backend em outra porta:

```powershell
python manage.py runserver 127.0.0.1:8001
```

Se mudar a porta do backend, atualize tambem a `baseURL` em:

```text
frontend/aguapei_frontend/src/services/api.js
```
