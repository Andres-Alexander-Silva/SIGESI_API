"""Reporta (y opcionalmente elimina) archivos huérfanos bajo MEDIA_ROOT.

Un archivo "huérfano" es uno que existe físicamente bajo MEDIA_ROOT pero al
que ningún FileField/ImageField de ningún modelo apunta. django-cleanup (ver
INSTALLED_APPS en settings.py) evita que se generen huérfanos *nuevos* a
partir de su instalación, pero no limpia retroactivamente los que ya se
acumularon antes (ver docs/HU-021_PLAN_IMPLEMENTACION.md, hallazgo H3).

Uso:
    python manage.py limpiar_huerfanos --dry-run   # solo reporta, no borra
    python manage.py limpiar_huerfanos              # reporta y elimina
"""
import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import FileField


class Command(BaseCommand):
    help = 'Reporta (y opcionalmente elimina) archivos huerfanos bajo MEDIA_ROOT.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo reporta los huerfanos encontrados, sin eliminarlos.',
        )

    def handle(self, *args, **options):
        media_root = os.path.realpath(settings.MEDIA_ROOT)
        referenciados = self._archivos_referenciados()

        huerfanos = []
        for dirpath, _dirnames, filenames in os.walk(media_root):
            for filename in filenames:
                abs_path = os.path.realpath(os.path.join(dirpath, filename))
                rel_path = os.path.relpath(abs_path, media_root).replace(os.sep, '/')
                if rel_path not in referenciados:
                    huerfanos.append(abs_path)

        if not huerfanos:
            self.stdout.write(self.style.SUCCESS('No se encontraron archivos huerfanos.'))
            return

        for path in huerfanos:
            self.stdout.write(f'  huerfano: {path}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'{len(huerfanos)} archivo(s) huerfano(s) encontrados '
                '(--dry-run: no se eliminó ninguno).'
            ))
            return

        eliminados = 0
        for path in huerfanos:
            try:
                os.remove(path)
                eliminados += 1
            except OSError as exc:
                self.stderr.write(f'No se pudo eliminar {path}: {exc}')

        self.stdout.write(self.style.SUCCESS(f'{eliminados} archivo(s) huerfano(s) eliminados.'))

    def _archivos_referenciados(self):
        """Conjunto de rutas relativas a MEDIA_ROOT que sí tienen fila en BD."""
        referenciados = set()
        for model in apps.get_models():
            campo_nombres = [
                f.name for f in model._meta.get_fields()
                if isinstance(f, FileField)
            ]
            if not campo_nombres:
                continue
            for row in model.objects.values(*campo_nombres):
                for nombre in campo_nombres:
                    valor = row.get(nombre)
                    if valor:
                        referenciados.add(str(valor).replace(os.sep, '/'))
        return referenciados
