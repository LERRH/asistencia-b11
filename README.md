# Registro automático de asistencia B-11

Consulta cada 10 minutos al bot de Telegram `@CGBVPClaudioBot` con `/quien B-11`,
guarda quién ingresó y a qué hora, y marca una salida referencial (hora en la
que una persona deja de aparecer en el reporte).

Corre automáticamente en **GitHub Actions** (repo privado
`LERRH/asistencia-b11`) — no depende de que ninguna PC esté encendida.

## Cómo funciona

- El bot es de terceros: no hay Bot API/token propio, así que este proyecto
  automatiza tu **cuenta personal de Telegram** (API de cliente, vía
  [Telethon](https://docs.telethon.dev/)) para enviar el comando como si lo
  escribieras tú.
- `poller.py` es un script "de un solo disparo": se conecta, pide el reporte,
  guarda los cambios en SQLite y termina. El bot responde primero con un
  mensaje "⏳ Consultando…" y luego lo **edita** con el reporte real —
  `poller.py` espera esa edición en vez de un mensaje nuevo.
- El "estado" de cada persona vive en la tabla `sesiones`:
  - `presente`: sigue apareciendo en el último reporte.
  - `salio`: dejó de aparecer; `hora_salida_estimada` es el momento del ciclo
    en que se detectó su ausencia (es referencial, no exacta — el sistema
    real del bot no informa la hora de salida). Margen de error: hasta ~10 min
    (el intervalo entre corridas).
- Si el bot no responde a tiempo, o el reporte no se puede parsear con
  confianza (formato inesperado, grado nuevo no reconocido, etc.), el ciclo
  **no reconcilia nada** — evita marcar a todos como "salidos" por una falla
  transitoria. El intento fallido queda registrado en la tabla `snapshots`
  para diagnóstico.
- `asistencia.db` (la base de datos) se versiona en el propio repositorio: el
  workflow hace commit y push del archivo actualizado en cada corrida. Por
  eso hay que hacer `git pull` para ver los últimos datos localmente.

## Despliegue: GitHub Actions

Todo vive en `.github/workflows/poller.yml`, con estos secrets configurados
en el repo (Settings → Secrets and variables → Actions):

- `TG_API_ID`, `TG_API_HASH`, `TG_PHONE` — credenciales de la cuenta de
  Telegram (de https://my.telegram.org).
- `TG_SESSION_B64` — el archivo `asistencia.session` (ya autenticado)
  codificado en base64. **Esto equivale a la llave de acceso completa a la
  cuenta de Telegram — por eso el repo debe quedar SIEMPRE privado.**
- `BOT_USERNAME` (`CGBVPClaudioBot`) y `COMPANIA` (`B-11`).

El cron actual es `*/10 * * * *` (cada 10 minutos). GitHub Actions no permite
programar corridas más seguido que cada 5 minutos, y en plan gratuito de
repos privados el límite es de ~2000 minutos de Actions al mes — a 10 min de
intervalo se usan ~4300 min/mes, por lo que **es esperable que GitHub deje de
correr el workflow automáticamente si se agota la cuota gratuita antes de fin
de mes** (no cobra sin autorización explícita de método de pago).

Para reautenticar si la sesión se invalida algún día (ej. la cerraste desde
"Dispositivos activos" de Telegram):
1. Corre `python login.py request` y `python login.py confirm <codigo>`
   localmente (regenera `asistencia.session`).
2. Sube el nuevo archivo como secret:
   ```
   base64 -w0 asistencia.session | gh secret set TG_SESSION_B64 --repo LERRH/asistencia-b11
   ```

## Setup inicial / pruebas locales

1. Consigue credenciales de la API de Telegram en https://my.telegram.org
   (API development tools) usando la cuenta que le habla al bot.
2. Copia `.env.example` a `.env` y completa `TG_API_ID`, `TG_API_HASH`,
   `TG_PHONE`, `BOT_USERNAME`, `COMPANIA`.
3. Instala dependencias:
   ```
   pip install -r requirements.txt
   ```
4. Login (en dos pasos, sin prompts interactivos):
   ```
   python login.py request
   python login.py confirm <codigo>
   ```
   Si tu cuenta tiene verificación en dos pasos, corre tú mismo
   `python login.py password <tu_clave>` (esa clave no debe compartirse).
5. Prueba manual:
   ```
   python poller.py
   python query.py presentes
   ```

## Consultas

```
git pull                            # trae los ultimos datos del workflow
python query.py presentes           # quién está presente ahora mismo
python query.py historial --dias 7  # ingresos/salidas de los últimos 7 días
```

## Notas

- Solo se monitorea la compañía definida en `COMPANIA` (por defecto `B-11`).
  Para monitorear otra, cambia esa variable o duplica el proyecto con otro
  `.env`/`DB_PATH`.
- Revisa la pestaña **Actions** del repo para ver el historial de corridas
  (éxito/falla) y la tabla `snapshots` (columna `ok`/`error`) para detectar
  si el bot cambió su formato de respuesta.
