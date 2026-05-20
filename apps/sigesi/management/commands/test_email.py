"""Comando de diagnóstico para el envío de correos de recuperación.

Envía el correo de recuperación real (misma plantilla y ruta de envío que
usa `RecuperacionView`) a un destinatario arbitrario e imprime el resultado.

Sirve para comparar la entrega entre dominios (p. ej. @gmail.com vs
@ufps.edu.co) sin pasar por el frontend ni crear un usuario:

    python manage.py test_email destinatario@ufps.edu.co
    python manage.py test_email destinatario@gmail.com --nombre "Prueba SIGESI"

Recuerda: un resultado "sent" significa que el servidor SMTP (Gmail) aceptó
el mensaje; la entrega final puede fallar por filtrado/cuarentena del receptor.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.sigesi.utils.email_service import enviar_correo_recuperacion


class Command(BaseCommand):
    help = "Envía un correo de recuperación de prueba para diagnosticar la entrega SMTP."

    def add_arguments(self, parser):
        parser.add_argument(
            "destinatario",
            help="Dirección de correo a la que enviar el mensaje de prueba.",
        )
        parser.add_argument(
            "--nombre",
            default="Usuario de Prueba",
            help="Nombre mostrado en el saludo del correo (por defecto: 'Usuario de Prueba').",
        )

    def handle(self, *args, **options):
        destinatario = options["destinatario"]
        nombre = options["nombre"]

        # Mostrar la configuración efectiva para que el diagnóstico sea autocontenido.
        self.stdout.write("Configuración SMTP en uso:")
        self.stdout.write(f"  EMAIL_HOST       = {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        self.stdout.write(f"  EMAIL_HOST_USER  = {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"  EMAIL_USE_TLS    = {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  DEFAULT_FROM     = {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"  EMAIL_BACKEND    = {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Enviando correo de prueba a: {destinatario}\n")

        # Token de relleno: este comando solo prueba la entrega, no el flujo de reseteo.
        resultado = enviar_correo_recuperacion(
            destinatario_email=destinatario,
            destinatario_nombre=nombre,
            token="TOKEN_DE_PRUEBA_DIAGNOSTICO",
        )

        if resultado and resultado.get("status") == "sent":
            self.stdout.write(self.style.SUCCESS(
                f"OK: el servidor SMTP aceptó el mensaje para {destinatario}.\n"
                "    La entrega final NO está garantizada — revisa Spam/cuarentena "
                "del destinatario si no llega."
            ))
        else:
            self.stderr.write(self.style.ERROR(
                f"FALLO al enviar a {destinatario}: {resultado}"
            ))
