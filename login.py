"""Login inicial de Telethon, en pasos no interactivos (para correr desde
un entorno sin stdin, como esta sesión de Claude Code).

Uso:
    python login.py request              -> pide el código de verificación
    python login.py confirm <codigo>     -> confirma el código y crea la sesión
    python login.py password <clave2fa>  -> solo si la cuenta tiene verificación
                                             en dos pasos (ejecutar el usuario
                                             mismo, no compartir la clave)
    python login.py status               -> confirma si ya hay una sesión válida
"""
import asyncio
import sys

from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
PHONE = os.environ["TG_PHONE"]
SESSION = os.getenv("TG_SESSION", "asistencia")

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

PHONE_CODE_HASH_FILE = f"{SESSION}.phone_code_hash"


async def cmd_request():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    sent = await client.send_code_request(PHONE)
    with open(PHONE_CODE_HASH_FILE, "w") as f:
        f.write(sent.phone_code_hash)
    await client.disconnect()
    print("Código enviado a tu cuenta de Telegram. Pásamelo y correré:")
    print("  python login.py confirm <codigo>")


async def cmd_confirm(code: str):
    with open(PHONE_CODE_HASH_FILE) as f:
        phone_code_hash = f.read().strip()

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    try:
        await client.sign_in(PHONE, code=code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        print("Esta cuenta tiene verificación en dos pasos.")
        print("Ejecuta tú mismo (no la compartas conmigo): python login.py password <tu_clave>")
        await client.disconnect()
        return
    me = await client.get_me()
    await client.disconnect()
    os.remove(PHONE_CODE_HASH_FILE)
    print(f"Login exitoso como {me.first_name} (@{me.username}). Sesión guardada en {SESSION}.session")


async def cmd_password(password: str):
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    me = await client.sign_in(password=password)
    await client.disconnect()
    if os.path.exists(PHONE_CODE_HASH_FILE):
        os.remove(PHONE_CODE_HASH_FILE)
    print(f"Login exitoso como {me.first_name} (@{me.username}). Sesión guardada en {SESSION}.session")


async def cmd_status():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    ok = await client.is_user_authorized()
    if ok:
        me = await client.get_me()
        print(f"Sesión válida: {me.first_name} (@{me.username})")
    else:
        print("No hay sesión válida todavía.")
    await client.disconnect()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "request":
        asyncio.run(cmd_request())
    elif cmd == "confirm":
        asyncio.run(cmd_confirm(sys.argv[2]))
    elif cmd == "password":
        asyncio.run(cmd_password(sys.argv[2]))
    elif cmd == "status":
        asyncio.run(cmd_status())
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
