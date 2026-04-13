"""
Migración de esquema: reestructura los modelos Menu, Opcion y Permiso.

Cambios:
  Menu    → renombra tabla, quita orden/url/menu_padre/timestamps,
            renombra is_active→estado, añade unique a nombre e icono.
  Opcion  → renombra tabla, quita codigo/descripcion/accion/timestamps,
            renombra is_active→estado, añade url, cambia FK a RESTRICT.
  Permiso → renombra tabla, quita permitido/timestamps,
            añade puede_consultar/crear/actualizar/eliminar, cambia FK a RESTRICT.
"""

import django.db.models.deletion
from django.db import migrations, models


def limpiar_datos_viejos(apps, schema_editor):
    """Borra permisos, opciones y menús existentes antes de restructurar.
    Los datos correctos se cargan en la migración 0003."""
    apps.get_model('sigesi', 'Permiso').objects.all().delete()
    apps.get_model('sigesi', 'Opcion').objects.all().delete()
    apps.get_model('sigesi', 'Menu').objects.all().delete()


class Migration(migrations.Migration):

    # atomic=False permite que cada operación corra en su propia transacción,
    # evitando el error de PostgreSQL por triggers FK pendientes al mezclar
    # DELETE con ALTER TABLE en la misma transacción.
    atomic = False

    dependencies = [
        ('sigesi', '0001_initial'),
    ]

    operations = [

        # Limpiar datos antes de alterar el esquema
        migrations.RunPython(limpiar_datos_viejos, migrations.RunPython.noop),

        # ── MENU ────────────────────────────────────────────────────────────

        # Quitar campos que ya no existen
        migrations.RemoveField(model_name='menu', name='orden'),
        migrations.RemoveField(model_name='menu', name='url'),
        migrations.RemoveField(model_name='menu', name='menu_padre'),
        migrations.RemoveField(model_name='menu', name='created_at'),
        migrations.RemoveField(model_name='menu', name='updated_at'),

        # Reemplazar is_active por estado
        migrations.RemoveField(model_name='menu', name='is_active'),
        migrations.AddField(
            model_name='menu',
            name='estado',
            field=models.BooleanField(default=True),
        ),

        # Ajustar nombre e icono (unique, icono ya no blank)
        migrations.AlterField(
            model_name='menu',
            name='nombre',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='menu',
            name='icono',
            field=models.CharField(max_length=50, unique=True),
        ),

        # Renombrar tabla
        migrations.AlterModelTable(name='menu', table='menus'),

        # ── OPCION ──────────────────────────────────────────────────────────

        # Quitar campos que ya no existen
        migrations.RemoveField(model_name='opcion', name='codigo'),
        migrations.RemoveField(model_name='opcion', name='descripcion'),
        migrations.RemoveField(model_name='opcion', name='accion'),
        migrations.RemoveField(model_name='opcion', name='created_at'),
        migrations.RemoveField(model_name='opcion', name='updated_at'),

        # Reemplazar is_active por estado
        migrations.RemoveField(model_name='opcion', name='is_active'),
        migrations.AddField(
            model_name='opcion',
            name='estado',
            field=models.BooleanField(default=True),
        ),

        # Añadir url
        migrations.AddField(
            model_name='opcion',
            name='url',
            field=models.CharField(max_length=100, unique=True, default=''),
            preserve_default=False,
        ),

        # Ajustar nombre
        migrations.AlterField(
            model_name='opcion',
            name='nombre',
            field=models.CharField(max_length=100),
        ),

        # Cambiar FK menu a RESTRICT
        migrations.AlterField(
            model_name='opcion',
            name='menu',
            field=models.ForeignKey(
                null=False,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='opciones',
                to='sigesi.menu',
            ),
        ),

        # Renombrar tabla
        migrations.AlterModelTable(name='opcion', table='opciones'),

        # ── PERMISO ─────────────────────────────────────────────────────────

        # Quitar campos viejos
        migrations.RemoveField(model_name='permiso', name='permitido'),
        migrations.RemoveField(model_name='permiso', name='created_at'),
        migrations.RemoveField(model_name='permiso', name='updated_at'),

        # Añadir los 4 campos CRUD
        migrations.AddField(
            model_name='permiso',
            name='puede_consultar',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='permiso',
            name='puede_crear',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='permiso',
            name='puede_actualizar',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='permiso',
            name='puede_eliminar',
            field=models.BooleanField(default=False),
        ),

        # Quitar verbose_name del campo rol
        migrations.AlterField(
            model_name='permiso',
            name='rol',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('administrador',      'Administrador'),
                    ('director_grupo',     'Director de Grupo'),
                    ('director_semillero', 'Director de Semillero'),
                    ('lider_estudiantil',  'Líder Estudiantil'),
                    ('estudiante',         'Estudiante'),
                    ('comite',             'Comité de Investigación'),
                ],
            ),
        ),

        # Cambiar FK opcion a RESTRICT
        migrations.AlterField(
            model_name='permiso',
            name='opcion',
            field=models.ForeignKey(
                null=False,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='permisos',
                to='sigesi.opcion',
            ),
        ),

        # Renombrar tabla
        migrations.AlterModelTable(name='permiso', table='permisos'),
    ]
