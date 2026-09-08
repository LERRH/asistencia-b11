"""Consulta rápida sobre el registro de asistencia.

Uso:
    python query.py presentes
    python query.py historial [--dias N]
"""
import sys
from datetime import timedelta

from dotenv import load_dotenv

import db
from tz import ahora_lima

load_dotenv()


def presentes():
    with db.conectar() as conn:
        filas = conn.execute(
            """SELECT compania, grado, nombre, hora_ingreso_reportada, ultima_deteccion
               FROM sesiones WHERE estado = 'presente'
               ORDER BY compania, hora_ingreso_reportada"""
        ).fetchall()

    if not filas:
        print("Nadie presente actualmente según el último ciclo.")
        return

    for f in filas:
        print(f"[{f['compania']}] {f['grado']} {f['nombre']} — ingresó {f['hora_ingreso_reportada']} "
              f"(visto por última vez: {f['ultima_deteccion']})")


def historial(dias: int):
    desde = (ahora_lima() - timedelta(days=dias)).isoformat(sep=" ", timespec="seconds")
    with db.conectar() as conn:
        filas = conn.execute(
            """SELECT compania, grado, nombre, hora_ingreso_reportada, hora_salida_estimada, estado
               FROM sesiones WHERE hora_ingreso_reportada >= ?
               ORDER BY hora_ingreso_reportada DESC""",
            (desde,),
        ).fetchall()

    if not filas:
        print(f"Sin registros en los últimos {dias} día(s).")
        return

    for f in filas:
        salida = f["hora_salida_estimada"] or ("presente" if f["estado"] == "presente" else "?")
        print(f"[{f['compania']}] {f['grado']} {f['nombre']} — ingreso {f['hora_ingreso_reportada']} "
              f"| salida (referencial): {salida}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "presentes":
        presentes()
    elif cmd == "historial":
        dias = 1
        if "--dias" in sys.argv:
            dias = int(sys.argv[sys.argv.index("--dias") + 1])
        historial(dias)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
