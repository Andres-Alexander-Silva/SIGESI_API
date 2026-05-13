from django.utils import timezone
import pytz


def get_now_colombia():
    bogota_tz = pytz.timezone("America/Bogota")
    hora_colombia = timezone.now().astimezone(bogota_tz)
    return hora_colombia


def semestre_actual():
    """Retorna el semestre académico vigente con formato 'YYYY-1' o 'YYYY-2'."""
    now = get_now_colombia()
    half = 1 if now.month <= 6 else 2
    return f"{now.year}-{half}"
