# Scripts PostgreSQL Legados

Esta pasta guarda scripts SQL criados antes da estrutura oficial por migrations do Django.

Use estes arquivos apenas como referencia historica ou apoio pontual de diagnostico. Para criar ou atualizar o banco, o fluxo principal do projeto agora e:

```powershell
cd C:\Users\pytag\BRAVO\backend
python manage.py migrate
```

Os catalogos obrigatorios sao carregados pela migration `api.0003_seed_required_catalogs`.
