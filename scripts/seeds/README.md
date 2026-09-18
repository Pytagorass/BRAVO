# Seeds BRAVO

Os seeds ficam separados por finalidade:

- `required/`: fallback manual para catalogos minimos e configuracoes operacionais sem dados fake.
- `dev/`: dados convenientes para ambiente local, como usuario admin padrao.
- `demo/`: massa de demonstracao para telas, graficos e testes manuais.

Fluxo recomendado em um banco novo:

```powershell
cd C:\Users\pytag\BRAVO\backend
python manage.py migrate
```

As migrations ja carregam os catalogos obrigatorios do sistema pela migration `api.0003_seed_required_catalogs`.

O SQL de `required/` deve ser usado apenas como fallback manual, caso voce precise reaplicar os catalogos fora do fluxo do Django:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://postgres:123@localhost:5432/Barco_Hotel" -f "C:\Users\pytag\BRAVO\scripts\seeds\required\0001_catalogos_base.sql"
```

Usuario admin local:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://postgres:123@localhost:5432/Barco_Hotel" -f "C:\Users\pytag\BRAVO\scripts\seeds\dev\0001_usuario_admin_dev.sql"
```

Usuarios locais por nivel de acesso:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://postgres:123@localhost:5432/Barco_Hotel" -f "C:\Users\pytag\BRAVO\scripts\seeds\dev\0002_usuarios_niveis_acesso_dev.sql"
```

Dados demo devem ser opcionais e nunca obrigatorios para producao.
