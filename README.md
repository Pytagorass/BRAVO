# BRAVO - Barco-Hotel Aguapei

Sistema de gestao para operacao de barco-hotel, com backend em Django e frontend em React.

O projeto usa PostgreSQL como banco de dados e SQL direto no backend, sem ORM para as regras principais da aplicacao.

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
  scripts/postgres/          Scripts auxiliares de banco
  schema.sql                 Estrutura principal do banco
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

Crie o banco no PostgreSQL com o nome `Barco_Hotel` e execute o arquivo `schema.sql`.

No `psql`:

```sql
\i C:/Users/pytag/BRAVO/schema.sql
```

No Windows, se o `psql` nao estiver no PATH, use o caminho completo:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://postgres:123@localhost:5432/Barco_Hotel" -f "C:\Users\pytag\BRAVO\schema.sql"
```

O script cria as tabelas principais e um usuario administrador.

## Login Padrao

```text
Email: admin@aguapei.local
Senha: 123456
```

## Rodando o Backend

Abra um terminal PowerShell:

```powershell
cd C:\Users\pytag\BRAVO\backend
python -m pip install Django django-cors-headers PyJWT bcrypt psycopg2-binary
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
- `backend/api/views.py`: endpoints da API e regras principais.
- `backend/api/urls.py`: rotas da API.
- `frontend/aguapei_frontend/src/services/api.js`: configuracao do Axios e URL do backend.
- `schema.sql`: criacao das tabelas e dados iniciais.

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
