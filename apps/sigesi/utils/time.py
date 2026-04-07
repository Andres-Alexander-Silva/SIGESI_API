from django.utils import timezone
import pytz


def get_now_colombia():
    bogota_tz = pytz.timezone("America/Bogota")
    hora_colombia = timezone.now().astimezone(bogota_tz)
    return hora_colombia
