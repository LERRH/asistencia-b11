# Registro automático de asistencia B-11

Consulta cada 30 minutos al bot de Telegram `@CGBVPClaudeBot` con `/quien B-11`,
guarda quién ingresó y a qué hora, y marca una salida referencial (hora en la
que una persona deja de aparecer en el reporte).

## Cómo funciona

- El bot es de terceros: no hay Bot API/token propio, así que este proyecto
  automatiza tu **cuenta personal de Telegram** (API de cliente, vía
  [Telethon](https://docs.telethon.dev/)) para enviar el comando como si lo
  escribieras tú.
- `poller.py` es un script "de un solo disparo": se conecta, pide el reporte,
  guarda los cambios en SQLite y termina. Se programa para correr cada 30 min
  vía cron (más robusto ante caídas que un proceso de larga duración).
- El "estado" de cada persona vive en la tabla `sesiones`:
  - `presente`: sigue apareciendo en el último reporte.
  - `salio`: dejó de aparecer; `hora_salida_estimada` es el momento del ciclo
    en que se detectó su ausencia (es referencial, no exacta — el sistema
    real del bot no informa la hora de salida).
- Si el bot no responde a tiempo, o el reporte no se puede parsear con
  confianza (formato inesperado), el ciclo **no reconcilia nada** — evita
  marcar a todos como "salidos" por una falla transitoria. El intento fallido
  queda registrado en la tabla `snapshots` para diagnóstico.

## Setup inicial (local)

1. Consigue credenciales de la API de Telegram en https://my.telegram.org
   (API development tools) usando la cuenta que le habla al bot.
2. Copia `.env.example` a `.env` y completa `TG_API_ID`, `TG_API_HASH`,
   `TG_PHONE` (con el número de esa cuenta, formato internacional).
3. Instala dependencias:
   ```
   pip install -r requirements.txt
   ```
4. Login (en dos pasos, sin prompts interactivos):
   ```
   python login.py request
   ```
   Te llegará un código por Telegram. Luego:
   ```
   python login.py confirm <codigo>
   ```
   Si tu cuenta tiene verificación en dos pasos, verás un aviso pidiendo que
   corras tú mismo `python login.py password <tu_clave>` (esa clave no debe
   compartirse, así que ese paso lo ejecutas directamente en tu terminal).

   Esto genera `asistencia.session`: es el archivo que reemplaza tener que
   volver a iniciar sesión.

5. Prueba manual:
   ```
   python poller.py
   python query.py presentes
   ```

## Despliegue en el VPS

1. Copia **todo** el proyecto al VPS, incluyendo `asistencia.session` y `.env`
   (no hace falta repetir el login allá).
2. En el VPS:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python poller.py        # prueba manual
   python query.py presentes
   ```
3. Programa el cron (cada 30 minutos):
   ```
   crontab -e
   ```
   agrega:
   ```
   */30 * * * * cd /ruta/al/proyecto && venv/bin/python poller.py >> logs/poller.log 2>&1
   ```
   (crea la carpeta `logs/` antes: `mkdir logs`).

## Consultas

```
python query.py presentes           # quién está presente ahora mismo
python query.py historial --dias 7  # ingresos/salidas de los últimos 7 días
```

## Notas

- Solo se monitorea la compañía definida en `COMPANIA` dentro de `.env`
  (por defecto `B-11`). Para monitorear otra, cambia esa variable o duplica
  el proyecto con otro `.env`/`DB_PATH`.
- La hora de salida es **referencial**: es la hora del ciclo de 30 minutos en
  que la persona dejó de verse, no el momento exacto en que salió del
  sistema real. El margen de error máximo es de ~30 minutos.
- Revisa periódicamente `logs/poller.log` y la tabla `snapshots` (columna
  `ok`/`error`) para detectar si el bot cambió su formato de respuesta.
