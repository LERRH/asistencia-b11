import re
from dataclasses import dataclass
from datetime import datetime, timedelta

LINE_RE = re.compile(
    r"^[•\-\*]\s*(.+?)\s*[—\-]\s*(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})\s*$"
)
HEADER_COUNT_RE = re.compile(r"\((\d+)\)")


def _dividir_grado_nombre(texto: str) -> tuple[str, str]:
    """El bot escribe el grado en abreviatura mixta (Brig, Tnte, SubTnte,
    Tnte Brig...) y el primer apellido siempre en mayúsculas. Se usa eso
    como separador en vez de asumir que el grado es una sola palabra,
    porque hay grados compuestos (ej. 'Tnte Brig OCHOA OBA, ...')."""
    tokens = texto.split()
    for i, tok in enumerate(tokens):
        letras = tok.strip(",").strip()
        if letras and letras.isupper():
            return " ".join(tokens[:i]), " ".join(tokens[i:])
    return "", texto


@dataclass
class Presente:
    grado: str
    nombre: str
    hora_ingreso: datetime


@dataclass
class ReportePresentes:
    personas: list
    conteo_esperado: int | None
    lineas_no_parseadas: list


def _resolver_fecha(dia: int, mes: int, hora: int, minuto: int, ahora: datetime) -> datetime:
    candidata = datetime(ahora.year, mes, dia, hora, minuto)
    if candidata > ahora + timedelta(days=2):
        candidata = datetime(ahora.year - 1, mes, dia, hora, minuto)
    return candidata


def parsear_reporte(texto: str, ahora: datetime | None = None) -> ReportePresentes:
    """Parsea la respuesta de texto del bot (/quien <compania>) a una lista
    estructurada de personas presentes.

    No lanza excepción si una línea no matchea: la reporta en
    `lineas_no_parseadas` para que el llamador decida si es seguro reconciliar.
    """
    ahora = ahora or datetime.now()
    personas = []
    no_parseadas = []
    conteo_esperado = None

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue

        if conteo_esperado is None:
            m_header = HEADER_COUNT_RE.search(linea)
            if m_header and (linea.startswith("🚒") or "—" in linea):
                conteo_esperado = int(m_header.group(1))
                continue

        if not linea.startswith(("•", "-", "*")):
            continue

        m = LINE_RE.match(linea)
        if not m:
            no_parseadas.append(linea)
            continue

        combinado, dia, mes, hora, minuto = m.groups()
        grado, nombre = _dividir_grado_nombre(combinado)
        nombre = re.sub(r"\s+", " ", nombre).strip(" ,")
        nombre = nombre.replace(" ,", ",")
        hora_ingreso = _resolver_fecha(int(dia), int(mes), int(hora), int(minuto), ahora)
        personas.append(Presente(grado=grado, nombre=nombre, hora_ingreso=hora_ingreso))

    return ReportePresentes(
        personas=personas,
        conteo_esperado=conteo_esperado,
        lineas_no_parseadas=no_parseadas,
    )


def es_parseo_confiable(reporte: ReportePresentes) -> bool:
    """True si el parseo puede usarse para reconciliar la BD con seguridad."""
    if reporte.lineas_no_parseadas:
        return False
    if reporte.conteo_esperado is not None and len(reporte.personas) != reporte.conteo_esperado:
        return False
    return True
