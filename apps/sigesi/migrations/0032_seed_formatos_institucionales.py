"""Data migration: carga los 6 formatos institucionales ya existentes en disco
(antes hardcodeados en views/reports/formatos_docente_view.py::FORMATOS_DOCENTE)
en el nuevo modelo FormatoInstitucional (HU-021, fase F4).

No copia ni mueve ningún archivo: apunta cada fila al mismo path relativo
donde el .docx ya vive bajo MEDIA_ROOT/formatos/, preservando los slugs
existentes para no romper enlaces ya compartidos.

`informe-mensual` queda con tipo_vinculacion='catedratico' — es el único de
los seis que el paquete .zip de "Planta" excluía (ver el texto de ayuda en
SIGESI_CLIENT/src/pages/config/UsersPage.tsx: "Profesor de Planta: Todos los
formatos excepto Informe Mensual Semillero"). Los otros cinco quedan con
tipo_vinculacion=None (aplican a ambos).
"""
from django.db import migrations

FORMATOS = [
    # (slug, nombre, categoria, ruta_relativa, tipo_vinculacion)
    (
        'plan-accion-semillero',
        'Plan de Acción - Semilleros de Investigación',
        'planeacion',
        'formatos/planeacion/FO-IN-19 PLAN DE ACCION SEMILLEROS INV V2.docx',
        None,
    ),
    (
        'plan-accion-grupo',
        'Plan de Acción - Grupos de Investigación',
        'planeacion',
        'formatos/planeacion/FO-IN-17 PLAN DE ACCION GRUPOS INV V2.docx',
        None,
    ),
    (
        'gestion-semillero',
        'Informe de Gestión - Semillero de Investigación',
        'gestion',
        'formatos/gestion/FO-IN-14 INFORME GESTION SEM INV V2.docx',
        None,
    ),
    (
        'solicitud-horas-directores',
        'Solicitud de Horas de Investigación - Directores de Semillero',
        'administrativos_y_academicos',
        'formatos/administrativos_y_academicos/FO-IN-05  SOL HORAS INVESTIGACION DIR SEMILLEROS V2.docx',
        None,
    ),
    (
        'control-cumplimiento-produccion',
        'Control de Cumplimiento de Producción - Grupo o Semillero',
        'administrativos_y_academicos',
        'formatos/administrativos_y_academicos/FO-IN-08 CON CUMP PROD - GRUP O SEM V1.docx',
        None,
    ),
    (
        'informe-mensual',
        'Informe Mensual del Semillero',
        'mensual',
        'formatos/mensual/FORMATO INFORME MENSUAL SEMILLERO 0X - II SEM 2024.docx',
        'catedratico',
    ),
]


def cargar_datos(apps, schema_editor):
    FormatoInstitucional = apps.get_model('sigesi', 'FormatoInstitucional')
    for slug, nombre, categoria, ruta, tipo_vinculacion in FORMATOS:
        obj, _ = FormatoInstitucional.objects.get_or_create(
            slug=slug,
            defaults={
                'nombre': nombre,
                'categoria': categoria,
                'tipo_vinculacion': tipo_vinculacion,
                'estado': True,
            },
        )
        obj.archivo.name = ruta
        obj.save(update_fields=['archivo'])


def revertir_datos(apps, schema_editor):
    FormatoInstitucional = apps.get_model('sigesi', 'FormatoInstitucional')
    FormatoInstitucional.objects.filter(
        slug__in=[slug for slug, *_ in FORMATOS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0031_formato_institucional'),
    ]

    operations = [
        migrations.RunPython(cargar_datos, revertir_datos),
    ]
