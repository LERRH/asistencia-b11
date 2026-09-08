import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "asistencia.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compania TEXT NOT NULL,
    grado TEXT NOT NULL,
    nombre TEXT NOT NULL,
    hora_ingreso_reportada TEXT NOT NULL,
    primera_deteccion TEXT NOT NULL,
    ultima_deteccion TEXT NOT NULL,
    hora_salida_estimada TEXT,
    estado TEXT NOT NULL DEFAULT 'presente',
    UNIQUE(compania, nombre, hora_ingreso_reportada)
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compania TEXT NOT NULL,
    ts TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    ok INTEGER NOT NULL DEFAULT 1,
    error TEXT
);
"""


@contextmanager
def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def iso(dt: datetime) -> str:
    return dt.isoformat(sep=" ", timespec="seconds")


def guardar_snapshot(conn, compania: str, ts: datetime, raw_text: str, ok: bool, error: str | None):
    conn.execute(
        "INSERT INTO snapshots (compania, ts, raw_text, ok, error) VALUES (?, ?, ?, ?, ?)",
        (compania, iso(ts), raw_text, 1 if ok else 0, error),
    )


def reconciliar(conn, compania: str, presentes: list, ahora: datetime):
    """presentes: lista de objetos Presente (grado, nombre, hora_ingreso).

    Devuelve (nuevos, actualizados, marcados_como_salido).
    """
    ahora_iso = iso(ahora)
    claves_presentes = set()
    nuevos = 0
    actualizados = 0

    for p in presentes:
        ingreso_iso = iso(p.hora_ingreso)
        claves_presentes.add((compania, p.nombre, ingreso_iso))

        cur = conn.execute(
            """UPDATE sesiones SET ultima_deteccion = ?, grado = ?
               WHERE compania = ? AND nombre = ? AND hora_ingreso_reportada = ? AND estado = 'presente'""",
            (ahora_iso, p.grado, compania, p.nombre, ingreso_iso),
        )
        if cur.rowcount:
            actualizados += 1
            continue

        conn.execute(
            """INSERT INTO sesiones
               (compania, grado, nombre, hora_ingreso_reportada, primera_deteccion, ultima_deteccion, estado)
               VALUES (?, ?, ?, ?, ?, ?, 'presente')
               ON CONFLICT(compania, nombre, hora_ingreso_reportada)
               DO UPDATE SET estado = 'presente', ultima_deteccion = excluded.ultima_deteccion,
                             hora_salida_estimada = NULL""",
            (compania, p.grado, p.nombre, ingreso_iso, ahora_iso, ahora_iso),
        )
        nuevos += 1

    filas_presentes = conn.execute(
        "SELECT nombre, hora_ingreso_reportada FROM sesiones WHERE compania = ? AND estado = 'presente'",
        (compania,),
    ).fetchall()

    salidos = 0
    for fila in filas_presentes:
        clave = (compania, fila["nombre"], fila["hora_ingreso_reportada"])
        if clave not in claves_presentes:
            cur = conn.execute(
                """UPDATE sesiones SET estado = 'salio', hora_salida_estimada = ?
                   WHERE compania = ? AND nombre = ? AND hora_ingreso_reportada = ? AND estado = 'presente'""",
                (ahora_iso, compania, fila["nombre"], fila["hora_ingreso_reportada"]),
            )
            salidos += cur.rowcount

    return nuevos, actualizados, salidos
