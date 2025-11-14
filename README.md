# Barco-Hotel (Aguapeí)

Sistema de gestão para o Barco-Hotel Aguapeí. O backend usa Django com SQL puro (sem ORM) e o frontend é React.

## Requisitos

- PostgreSQL 13+
- Python 3.11+ com `pip`
- Node.js 18+

## Preparando o Banco

1. Crie um banco vazio.
2. Execute `schema.sql` no PgAdmin/psql:
   ```sql
   \i /caminho/para/schema.sql
   ```
   O script cria tabelas, índices e um usuário administrador (`admin@aguapei.local / 123456`).
3. Para gerar hashes personalizados:
   ```python
   import bcrypt
   bcrypt.hashpw("sua_senha".encode(), bcrypt.gensalt()).decode()
   ```
   Atualize a tabela `usuario` com o hash resultante.

## Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py runserver
```

- Todas as views usam SQL puro via `django.db.connection`.
- Variáveis principais:
  - `backend/api/views.py`: criação/edição de reservas.
  - `schema.sql`: estrutura do banco.

## Frontend

```bash
cd frontend/aguapei_frontend
npm install
npm start
```

## Fluxo de Reserva

1. Selecionar titular/quarto.
2. Definir datas e status de pagamento.
3. Confirmar no modal de revisão.
4. Após salvar, o Gantt é atualizado automaticamente.

## Observações

- `reserva.fk_hospede_titular` guarda o titular; `reserva_hospede` armazena apenas acompanhantes.
- `status_pagamento` controla o que é exibido no frontend.
- O script `schema.sql` pode ser reaplicado em bancos vazios sem ajustes extras.**
