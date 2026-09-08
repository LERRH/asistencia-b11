from datetime import datetime
from zoneinfo import ZoneInfo

LIMA = ZoneInfo("America/Lima")


def ahora_lima() -> datetime:
    """Hora actual en Peru (UTC-5), como datetime naive para que combine
    directamente con las horas que reporta el bot (que tambien vienen en
    hora local de Peru, sin zona horaria explicita)."""
    return datetime.now(LIMA).replace(tzinfo=None)
