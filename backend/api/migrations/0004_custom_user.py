from django.db import migrations, models

import api.models


def prefix_legacy_bcrypt_passwords(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE usuario
            SET senha = 'legacy_bcrypt$' || senha
            WHERE senha LIKE '$2%'
              AND senha NOT LIKE 'legacy_bcrypt$%';
            """
        )


def unprefix_legacy_bcrypt_passwords(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE usuario
            SET senha = substring(senha from length('legacy_bcrypt$') + 1)
            WHERE senha LIKE 'legacy_bcrypt$%';
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('api', '0003_seed_required_catalogs'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True, verbose_name='last login'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='is_superuser',
            field=models.BooleanField(
                default=False,
                help_text='Designates that this user has all permissions without explicitly assigning them.',
                verbose_name='superuser status',
            ),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='usuario',
                    old_name='senha',
                    new_name='password',
                ),
                migrations.AlterField(
                    model_name='usuario',
                    name='password',
                    field=models.CharField(db_column='senha', max_length=255),
                ),
                migrations.AlterField(
                    model_name='usuario',
                    name='email_usuario',
                    field=models.CharField(max_length=100, unique=True),
                ),
            ],
            database_operations=[],
        ),
        migrations.AddField(
            model_name='usuario',
            name='groups',
            field=models.ManyToManyField(
                blank=True,
                db_table='usuario_groups',
                related_name='usuarios_custom',
                related_query_name='usuario_custom',
                to='auth.group',
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='user_permissions',
            field=models.ManyToManyField(
                blank=True,
                db_table='usuario_user_permissions',
                related_name='usuarios_custom',
                related_query_name='usuario_custom',
                to='auth.permission',
            ),
        ),
        migrations.RunPython(prefix_legacy_bcrypt_passwords, unprefix_legacy_bcrypt_passwords),
        migrations.AlterModelManagers(
            name='usuario',
            managers=[
                ('objects', api.models.UsuarioManager()),
            ],
        ),
    ]
