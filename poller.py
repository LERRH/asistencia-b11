"""Un ciclo de consulta al bot de asistencia. Pensado para ser invocado por
cron/Tarea programada cada 30 minutos (proceso 'one-shot', no un loop)."""
import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient

import db
from parser import parsear_reporte, es_parseo_confiable
from tz import ahora_lima

load_dotenv()

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.getenv("TG_SESSION", "asistencia")
BOT_USERNAME = os.environ["BOT_USERNAME"]
COMPANIA = os.environ["COMPANIA"]
TIMEOUT_RESPUESTA = 20


async def consultar_bot(client: TelegramClient) -> str:
    async with client.conversation(BOT_USERNAME, timeout=TIMEOUT_RESPUESTA) as conv:
        await conv.send_message(f"/quien {COMPANIA}")
        respuesta = await conv.get_response()
        if "consultando" in respuesta.raw_text.lower():
            # El bot manda un mensaje "placeholder" y luego lo EDITA con el
            # reporte real, en vez de mandar un mensaje nuevo.
            respuesta = await conv.get_edit(timeout=TIMEOUT_RESPUESTA)
        return respuesta.raw_text


async def ejecutar_ciclo():
    ahora = ahora_lima()
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("ERROR: no hay sesión autenticada. Corre login.py primero.", file=sys.stderr)
        await client.disconnect()
        sys.exit(1)

    error = None
    texto = None
    try:
        texto = await consultar_bot(client)
    except asyncio.TimeoutError:
        error = "timeout esperando respuesta del bot"
    except Exception as exc:  # noqa: BLE001
        error = f"error consultando bot: {exc}"
    finally:
        await client.disconnect()

    with db.conectar() as conn:
        if error:
            db.guardar_snapshot(conn, COMPANIA, ahora, texto or "", ok=False, error=error)
            print(f"[{ahora}] FALLÓ el ciclo: {error}", file=sys.stderr)
            sys.exit(1)

        reporte = parsear_reporte(texto, ahora=ahora)
        confiable = es_parseo_confiable(reporte)

        if not confiable:
            motivo = (
                f"lineas_no_parseadas={reporte.lineas_no_parseadas!r} "
                f"conteo_esperado={reporte.conteo_esperado} obtenido={len(reporte.personas)}"
            )
            db.guardar_snapshot(conn, COMPANIA, ahora, texto, ok=False, error=motivo)
            print(f"[{ahora}] Parseo NO confiable, no se reconcilió: {motivo}", file=sys.stderr)
            sys.exit(1)

        db.guardar_snapshot(conn, COMPANIA, ahora, texto, ok=True, error=None)
        nuevos, actualizados, salidos = db.reconciliar(conn, COMPANIA, reporte.personas, ahora)
        print(
            f"[{ahora}] OK: {len(reporte.personas)} presentes "
            f"(nuevos={nuevos}, actualizados={actualizados}, marcados_salio={salidos})"
        )


if __name__ == "__main__":
    asyncio.run(ejecutar_ciclo())
