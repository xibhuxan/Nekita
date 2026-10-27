# ADR 0002: presupuesto de RAM en reposo (150 → 200 MB)

Estado: aceptado · Fase 7

## Contexto
La spec fijaba RSS en reposo ≤ 150 MB. Medido en desarrollo (Python 3.13, aiogram
3.x, bot conectado a Telegram real, unos 7 minutos en marcha): **187 MB**
(VmRSS = VmHWM). Disco del venv: 157 MB.

Desglose del arranque (RSS tras cada import, medido con `ru_maxrss`):

| Import | RSS |
|---|---|
| intérprete | 11 MB |
| asyncio + sqlite3 | 19 MB |
| pydantic + pydantic-settings | 32 MB |
| httpx | 23 MB |
| aiohttp | 36 MB |
| **aiogram** | **167 MB** |
| nekita completo | 171 MB |

aiogram construye con pydantic los ~900 modelos de la API de Telegram al importarse:
son unos 130 MB que no dependen del uso del bot.

## Decisión
Se mantiene aiogram y se sube el presupuesto en reposo a **≤ 200 MB**. Pico y
`MemoryMax=400M` no cambian. Sin FastAPI ni uvicorn ya hemos quitado lo evitable.

## Alternativas descartadas
- Cliente propio de Bot API con `httpx`: ahorraría ~130 MB, pero obliga a mantener
  tipos, filtros, polling y reintentos propios. No compensa en un servidor de 1 GB.
- Aligerar los modelos de aiogram: no es una opción soportada.

## Consecuencias
- Con 1 GB de RAM quedan ~800 MB libres: suficiente.
- ⚠️ El RSS **en pico** (descargando una imagen) y la medición en el servidor real
  siguen pendientes; se anotarán aquí cuando se hagan.
