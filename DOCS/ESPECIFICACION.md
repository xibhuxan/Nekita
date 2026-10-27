# 🐱 Nekita (Python) — Especificación y plan por fases

> **Estado: solo especificación. No hay código todavía.** Define *qué* debe hacer
> el bot, *con qué* se construye, *cómo* se organiza y *en qué orden* se hace,
> con criterios de "terminado" medibles por fase.
>
> Rama `python`: historial nuevo (huérfana), sin código ni commits de la versión anterior.

**Marcas de evidencia**

| Marca | Significado |
|---|---|
| ✅ | Comprobado en esta máquina al preparar la especificación |
| 🔎 | Tomado del comportamiento de la versión Node/NestJS, leído del código |
| 🆕 | Mejora o cambio de diseño respecto a la versión anterior |
| ⚠️ | Suposición o dato externo **sin verificar**: comprobar antes de depender de él |

---

## 1. Objetivo y alcance

**Objetivo:** reescribir Nekita en **Python (asyncio + aiogram)**, sin servidor
web, con buena estructura, **SQLite** como base de datos y una forma muy fácil
de añadir funciones nuevas, sin sobreingeniería y sobre un servidor pequeño
(**ligero a propósito**: pocas dependencias, sin Docker, sin Redis).

**Debe:**
1. Conservar **todas las funciones actuales** (sección 4), con los mismos textos.
2. Guardar el estado en SQLite con escritura inmediata (no "un guardado al día").
3. Arrancar, parar y recuperarse de fallos sin perder datos ni repetir ganadores.
4. Permitir añadir una función nueva **creando una carpeta**, sin tocar el núcleo (sección 6).
5. Poder probarse de forma automática, incluido el flujo completo de Telegram sin red.

**Planeado después (Fase 8, 6.4):** **IA remota** (el modelo corre en otro PC
por VPN o en la nube; el servidor solo hace llamadas HTTP salientes) y, si se
decide, avisos proactivos de las poles.

**No es objetivo (ahora):** panel web, servidor HTTP/FastAPI (retirado, decisión
17), varios idiomas, métricas con Prometheus, webhook, alta disponibilidad o
varias instancias (es **una** instancia con un SQLite local), ORM, colas, Redis.

---

## 2. Entorno de destino y presupuesto de recursos

| Recurso | Valor | Consecuencia |
|---|---|---|
| CPU | 1 core | Todo asíncrono en un solo proceso; sin varios workers |
| RAM | 1 GB | Proceso único; límite de memoria en systemd; descargas con tope |
| Disco | 8 GB | Logs con límite, copias rotadas, sin imágenes en disco |
| SO | Debian estable | Python y SQLite del sistema |

- ⚠️ **Python en destino:** Debian 13 trae Python 3.13 y es la versión objetivo (`requires-python >=3.13`). Comprobar en la máquina real: `python3 --version` y `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`. Se necesita **SQLite ≥ 3.37** para tablas `STRICT`; si fuera menor se quita `STRICT` y se compensa con `CHECK`.
- ✅ **En desarrollo** el Python del sistema es 3.14; `uv` descargó 3.13.16 y resolvió sin conflictos aiogram, pydantic-settings (⚠️ la resolución original incluía también fastapi y uvicorn, ya retirados; se vuelve a resolver en la Fase 0), httpx, pytest, pytest-asyncio, pytest-cov, ruff y mypy. Se desarrolla con **3.13** para igualar el destino.

**Presupuesto (hipótesis a medir en la Fase 6, no cifras garantizadas):**

| Métrica | Objetivo |
|---|---|
| RSS en reposo | ≤ 200 MB (ADR 0002; medido 187 MB) |
| RSS en pico (descargando una imagen) | ≤ 250 MB |
| CPU en reposo | < 2 % de un core |
| venv + código en disco | ≤ 400 MB |
| Arranque hasta "bot listo" | ≤ 5 s |

- `systemd` con `MemoryMax=400M`: si algo se desboca se reinicia solo el bot, no la máquina.
- ⚠️ Con 1 GB conviene un **swap de ~512 MB** como colchón; decidirlo en la Fase 6 según lo que ya tenga la máquina.

---
## 3. Decisiones de tecnología

Resueltas por defecto con el criterio "lo más simple que cumple". Son
**reversibles**; la sección 16 lista las que conviene que confirmes.

| # | Tema | Elegido | Por qué | Descartado |
|---|---|---|---|---|
| 1 | Cliente de Telegram | **aiogram 3** (✅ 3.31.0) | Asíncrono nativo; `Router` por módulo encaja con "una carpeta por función"; filtros, middlewares y `flags` | python-telegram-bot (válido, peor encaje de routers/flags) |
| 2 | Servidor web | **Ninguno** (punto de entrada `asyncio` simple) | Con polling no hace falta; menos RAM, disco y dependencias. Salud vigilada por systemd (10) | FastAPI + uvicorn (retirado: solo se justificaría con un panel web; ver decisión 17) |
| 3 | Recepción | **Long polling** | Sin dominio, HTTPS ni puertos abiertos | Webhook (Fase 8, opcional) |
| 4 | Base de datos | **SQLite** con **aiosqlite**, SQL explícito | Un fichero, ACID, sin servidor | PostgreSQL; SQLAlchemy+Alembic (pesados para ~7 tablas) |
| 5 | Migraciones | Ficheros `NNNN_nombre.sql` + `PRAGMA user_version`, ejecutor propio (~40 líneas) | Transparente y suficiente | Alembic |
| 6 | Configuración | **pydantic-settings** (✅ 2.16.0) | Errores legibles, variables `NEKITA_*` | `os.environ` a mano |
| 7 | HTTP saliente | **httpx** (✅ 0.28.1), un único `AsyncClient` | Timeouts, límites, fácil de simular en tests | requests (bloqueante) |
| 8 | Tareas programadas | Bucle propio sobre `asyncio` + `zoneinfo` | Solo habrá 1–2 (copias, limpieza) | APScheduler (se adopta si hay ≥3 tareas o recordatorios) |
| 9 | Entorno | **uv** + `pyproject.toml` + `uv.lock` | Instalaciones reproducibles | pip + requirements.txt |
| 10 | Calidad | **ruff**, **mypy --strict**, **pytest**, **pytest-asyncio**, **pytest-cov**, **pip-audit** | ✅ instalables | flake8/black/isort por separado |
| 11 | Despliegue | **systemd** en Debian, venv en `/opt/nekita` | Sin demonio Docker; sandbox y límites de systemd | Docker (opcional, `python:3.13-slim`) |
| 12 | Licencia | GPL-3.0 (se mantiene `LICENSE`) | Sin cambios | — |

**Dependencias de producción (solo estas):** `aiogram`, `pydantic-settings`,
`httpx`, `aiosqlite`, `tzdata`. (`pydantic` ya llega con aiogram.)
**Solo desarrollo:** `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `pip-audit`.

> ⚠️ `aiosqlite` **no se ha instalado ni probado** todavía; las demás versiones
> sí se resolvieron. Es una dependencia pequeña (envoltorio de hilo sobre
> `sqlite3`), pero se confirma en la Fase 0.

**Sobre FastAPI (retirado):** para un bot que solo hace polling aportaba poco.
La estructura del código viene de `core/` + `features/` y de la regla de
dependencias, no de FastAPI. El arranque y la parada (5.2) los orquesta
`app.py` con `asyncio`. Si algún día se quiere un panel web o un webhook, se
añade como feature/adaptador aparte (Fase 8) y el HTTP vive **solo** en esa
capa, así que reintroducirlo no toca `core/` ni `features/`.

**Medición temprana:** la RAM y el disco con aiogram + SQLite se miden en la
**Fase 0** en el servidor real (no esperar a la 6), junto con Python, SQLite y
`aiosqlite` (los ⚠️ de arriba).

**Sobre aiogram y el orden de mensajes:** aiogram procesa cada update como una
tarea independiente (`handle_as_tasks=True`), así que dos mensajes del mismo
chat pueden solaparse. La versión Node serializaba por chat. 🆕 Aquí se añade un
**middleware que serializa por `chat_id`** (un `asyncio.Lock` por chat, con
limpieza de los inactivos) para que "oro" y "plata" enviados seguidos se
evalúen en orden. Es imprescindible para la pole (sección 7.3) y se prueba.

---

## 4. Inventario funcional (lo que debe seguir haciendo)

Es el **contrato de compatibilidad**, tomado del código Node 🔎. Los textos
exactos están en el Apéndice A.

### 4.1 Comandos con `/`

| Comando | Categoría | Descripción (menú de Telegram) | Qué hace |
|---|---|---|---|
| `/start` | start | Mensaje de bienvenida | Texto de bienvenida |
| `/hola` | start | Saluda al usuario | `Hola, <nombre>-nya.` |
| `/help` | start | Lista de comandos disponibles | Lista **generada** desde el registro, por categoría; oculta los de admin a quien no lo es; añade el párrafo de frases libres |
| `/hora` | info | Hora actual en España | `Son las: HH:MM:SS` en `NEKITA_TZ` |
| `/dia` | info | Fecha actual | `Hoy es: DD-MM-YYYY` en `NEKITA_TZ` |
| `/id` | info | ID del chat actual | `El ID de este grupo es: <chat_id>` |
| `/neko` | images | Imagen aleatoria de un gato | Ver 4.4 |
| `/perro` | images | Imagen aleatoria de un perro | Ver 4.4 |
| `/cangrejo` | images | Imagen aleatoria de un cangrejo | Ver 4.4 |
| `/moneda` | images | Imagen aleatoria de una moneda | Ver 4.4 |
| `/pole` | pole | Leaderboard de pole del grupo | Top 10 de la pole principal (4.3). 🆕 Cada pole de `games.toml` añade **su propio comando** (`/pole_canaria`, `/pole_patitos`…), con descripción `Leaderboard de <title> del grupo` |
| `/health` | meta | Comprueba que el bot está vivo | `🐱 Nekita está viva! v<versión>` |
| `/stats` | meta | Estadísticas del bot (solo admin) | Ver 4.6 |

✅ Descripciones y categorías **verificadas** una a una contra los comandos de la versión anterior (Node).

Reglas comunes:
- Los comandos se **publican solos** en el menú "/" (`setMyCommands`); los `admin_only` **no**. Best-effort: si falla, el bot arranca igualmente.
- `/comando@OtroBot` **no** lo atiende este bot.
- Solo cuentan en estadísticas los comandos que terminaron **sin excepción**.
- 🆕 La versión sale de **una sola fuente** (metadatos del paquete, `importlib.metadata`).
- **Nombre en `/hola`:** `@username` o, si no hay, `first_name` ✅. **Ojo, en la pole es distinto:** se usa `username` **sin `@`** o, si no hay, `first_name` ✅ (ver 4.3). Se mantiene tal cual porque los puntos antiguos por nombre están guardados sin `@`.

---
### 4.2 Texto libre (sin `/`)

Se evalúa en este orden y **el primero que responde consume el mensaje**:
1. **Poles** (las palabras de `games.toml`: `oro`, `plata`, `bronce`, `pole canaria`…): solo en grupos (4.3).
2. **Nekomandos**: tabla frase → respuesta (4.5, Apéndice B).

Lo que no es texto (fotos, ediciones, altas de miembros) no se toca.

### 4.3 Poles

Una **pole** es un juego independiente **definido por datos**, no por código:
`features/pole/games.toml`. Cada grupo lleva su propia puntuación de cada pole;
añadir una pole nueva es añadir un bloque al fichero (y reiniciar).

| Campo | Significado | Ejemplo |
|---|---|---|
| `id` | Identificador estable (es la clave en la BD; no se cambia) | `canaria` |
| `title` | Nombre que se muestra | `pole canaria` |
| `command` | Comando que muestra su ranking (`[a-z0-9_]`, ≤ 32) | `pole_canaria` |
| `tz` | Zona IANA: define **cuándo empieza el día** de esa pole | `Atlantic/Canary` |
| `window` | *Opcional.* Franja local `[from, to)` en la que se puede ganar. Sin ella, **todo el día** | `22:22`–`22:23` |
| `positions` | Lista **ordenada** de puestos; cada uno con `prize`, `points` y `words` (una o varias palabras) | oro → 3 pts |

**Poles de partida** (las tres que has definido):

| `id` | Comando | Zona | Franja | Puestos (palabras → puntos) |
|---|---|---|---|---|
| `pole` | `/pole` | `Europe/Madrid` | todo el día | 🥇 `oro` o `pole` → 3 · 🥈 `plata` → 2 · 🥉 `bronce` → 1 (plata y bronce, de momento, sin alternativas) |
| `canaria` | `/pole_canaria` | `Atlantic/Canary` | todo el día | único puesto: `pole canaria` → **1** |
| `patitos` | `/pole_patitos` | `Europe/Madrid` | 22:22–22:23 | único puesto: `pole patitos` → **1** |

**Ejemplo de `games.toml`** (las tres poles de partida; es el contenido que debe tener el fichero en la Fase 5):

```toml
[[game]]
id = "pole"
title = "pole"
command = "pole"
tz = "Europe/Madrid"
  [[game.position]]
  prize = "la pole"
  points = 3
  words = ["oro", "pole"]
  [[game.position]]
  prize = "la plata"
  points = 2
  words = ["plata"]
  [[game.position]]
  prize = "el bronce"
  points = 1
  words = ["bronce"]

[[game]]
id = "canaria"
title = "pole canaria"
command = "pole_canaria"
tz = "Atlantic/Canary"
  [[game.position]]
  prize = "la pole canaria"
  points = 1
  words = ["pole canaria"]

[[game]]
id = "patitos"
title = "pole patitos"
command = "pole_patitos"
tz = "Europe/Madrid"
window = { from = "22:22", to = "22:23" }
  [[game.position]]
  prize = "la pole patitos"
  points = 1
  words = ["pole patitos"]
```

**Preparado para nombres alternativos:** `words` es **siempre una lista**, aunque hoy tenga un solo elemento. Dar a `plata` el alias `segundo`, por ejemplo, es cambiar `words = ["plata"]` por `words = ["plata", "segundo"]` y reiniciar: sin código, sin migración y sin tocar los puntos ya ganados (que se guardan por **puesto**, no por palabra). Las palabras se comparan **normalizadas** (4.5), así que `Plata`, `plata ` y `PLATA` son la misma. Test específico en 7.3 (k).

**Reglas**
- Solo en **grupos y supergrupos**. En privado, canales o mensajes sin usuario (admin anónimo) se **ignora**.
- El mensaje debe ser **exactamente** una de las palabras (no "contiene"), con la normalización de 4.5: minúsculas, sin acentos, espacios colapsados.
- **El día** de una pole es la fecha local en **su** zona y empieza a las **00:00** locales. `pole` cambia a las 00:00 de Madrid y `canaria` a las 00:00 de Canarias (01:00 de Madrid).
- Se gana **por orden** y solo el puesto que toca; la palabra de un puesto posterior no cuenta. Un juego con un único puesto se acaba con la primera victoria del día.
- Con `window`, solo cuenta si la hora local del mensaje está dentro de la franja. Sin ella se puede ganar **durante todo el día, hasta que se agoten los puestos de ese día**.
- Una persona gana **como mucho un puesto por día y por pole**; sí puede ganar a la vez en poles distintas.
- Cada puesto da sus puntos. La puntuación de una pole es **una sola, acumulada de todos los días**; los puntos se guardan en cada victoria, así que cambiar los puntos en el fichero no reescribe el pasado.
- Las palabras son **únicas entre todas las poles**: si dos poles comparten una, el bot **no arranca** y dice cuál (4.3.1).
- Al ganar: `¡Enhorabuena <nombre>! Has ganado <prize>-nya` (`la pole`, `la plata`, `el bronce`…). `<nombre>` es `username` **sin `@`** o, si no hay, `first_name`.
- Si el mensaje **no concede nada** (fuera de franja, puesto ya ganado, ya ganaste hoy), sigue hacia los nekomandos, como en Node. Así `pole patitos` a las 22:30 responde `A las 22:22, tú puedes-nya!`.
- **Ranking de cada pole:** su propio comando (`/pole`, `/pole_canaria`…), **top 10** de ese grupo, 🥇 🥈 🥉 y luego `#4`…`#10`. Los comandos salen **solos** en `/help` y en el menú de Telegram.
- Los puntos son del **usuario (id de Telegram)**, no del nombre; el ranking muestra el nombre actual.
- Los puntos de Node (por nombre) se importan a la pole `pole` (7.6) y se asignan al usuario cuando puntúa con ese nombre.

> 🆕 **Sin cron.** El día y la franja se **calculan** con `message.date` (el instante
> en que se envió, no cuando el bot lo procesa), así que todo es correcto aunque
> el bot haya estado parado o se reinicie. Se comparan campos de fecha/hora
> locales, nunca se suman milisegundos.

**Comprobado ✅** (Python 3.14 de esta máquina, `zoneinfo`):

| Instante (hora de Madrid) | Día de `pole` | Día de `canaria` |
|---|---|---|
| 21-oct 23:30 | 21-oct | 21-oct |
| 22-oct 00:00:01 | 22-oct | **21-oct** |
| 22-oct 00:30 | 22-oct | **21-oct** |
| 22-oct 01:00:01 | 22-oct | 22-oct |

Franja `22:22`–`22:23` (semiabierta): `22:21:59` no · `22:22:00` sí · `22:22:59` sí · `22:23:00` no. Probadas seis fechas alrededor de los dos cambios de hora de 2026 (28-29-30 de marzo y 24-25-26 de octubre, en Madrid): las 22:22 locales siguen dentro de la franja, y las 00:00 locales de los dos domingos de cambio existen y no son ambiguas. ⚠️ Canarias cambia a la vez que la península pero no se ha probado su zona por separado; es parte del test (h) de 7.3.

**Límites conocidos**
- Una `window` no puede cruzar la medianoche (se rechaza al cargar).
- Cambiar `games.toml` requiere reiniciar el bot.
- Si se quita una pole del fichero, sus datos siguen en la BD pero dejan de mostrarse.
- `message.date` tiene resolución de segundos: dos mensajes del mismo segundo se ordenan por el orden de proceso (determinista gracias a la serialización por chat).

#### 4.3.1 Validación al arrancar (error legible y `exit 1`)

`id` y `command` únicos y válidos (`[a-z0-9_]+`, el comando no puede chocar con otro de cualquier feature); `tz` IANA válida; `window` con `from < to`; al menos un puesto; `points` enteros ≥ 0; ninguna palabra vacía; `words` es una lista no vacía; **ninguna palabra repetida entre poles ni dentro de una pole, comparadas ya normalizadas** (`Plata` y `plata ` cuentan como la misma).

#### 4.3.2 Poles por definir

En los nekomandos actuales (Apéndice B) hay frases que sugieren más poles. **No están definidas**, así que siguen siendo solo texto hasta que me indiques su regla:

| Frase actual | Texto que responde hoy | Pregunta |
|---|---|---|
| `pole canaria` | "A las 12:00 de canarias" | Coherente con tu 00:00 Canarias si "12:00" es 12 a. m. ⚠️ (interpretación mía) |
| `pole peninsular` | "A las 11:00 de canarias" | 11 p. m. en Canarias = 00:00 de Madrid ⚠️. ¿Es la pole normal o un alias de `oro`? |
| `pole andaluza` | "a las 06:00 península está bien" | ¿Es una pole real? ¿Franja? |
| `pole palitos` | "A las 11:11" | ¿Franja y zona? ¿11:11 o 23:11? |
| `pole cuack`, `pole patitos canarias`, `pole cuack canarias` | "A las 22:22" | ¿`cuack` es otra palabra de `patitos`? ¿Las "canarias" son una pole aparte a las 22:22 de Canarias? |

---

### 4.4 Imágenes

| Comando | Fuente 🔎 | Particularidades |
|---|---|---|
| `/neko` | TheCatAPI (`limit=10`) | Lote de 10 URLs |
| `/perro` | random.dog (`woof.json?filter=mp4,webm`) | 5 peticiones en paralelo, se descartan vídeos y duplicados, reintentos por petición |
| `/cangrejo` | generatorfun.com (`Random-Crab-image-{1..19}.jpg`) | Lista fija de 19 |
| `/moneda` | Wikimedia Commons (API pública) | Categoría al azar (`Euro_coins`, `Gold_coins`, `Silver_coins`, `Coins_of_Spain`); solo `image/jpeg` y `image/png`; miniatura de 800 px; User-Agent identificativo obligatorio |

- **Caché de lotes** (TTL `NEKITA_CACHE_SEGUNDOS`, 300 s): un lote por clave y **cada petición consume una URL distinta**; cinco `/neko` seguidos no repiten. Lote vacío o caducado → se pide otro.
- 🆕 **Una sola petición de relleno por clave a la vez** (`asyncio.Lock`): 20 usuarios pidiendo `/neko` a la vez no hacen 20 llamadas a la API.
- 🆕 `/cangrejo` ya no hace un `HEAD` por petición; la lista se valida con un test *live* periódico.
- **Envío según extensión:** `gif` → `sendAnimation`; `mp4`/`webm` → `sendVideo`; resto → `sendPhoto`.
- **Plan B:** si Telegram no puede bajar la URL, el bot la **descarga** (máx. 10 MB, 15 s, con User-Agent) y la **sube**; si como foto la rechaza, la manda como **documento**. Animaciones y vídeos no tienen plan C: se informa del error.
- 🆕 Descargas en **streaming con tope de tamaño**, **máx. 2 simultáneas** (protege la RAM) y solo de URLs `https` de los **dominios permitidos** de cada proveedor (evita SSRF).
- Sin imagen → mensaje "Ahora mismo no veo…"; excepción → mensaje de error del comando (Apéndice A).
- ⚠️ Límites de Telegram (foto por URL ≈ 5 MB, subida ≈ 10 MB) tomados de la documentación de la Bot API; verificar al implementar.

### 4.5 Nekomandos

- Tabla `frase → respuesta` en un **fichero de datos** versionado (Apéndice B) más **overrides editables** sin redesplegar (7.5, Fase 4).
- **Normalización única** para claves y consultas: Unicode NFD, quitar diacríticos, minúsculas, espacios colapsados, `strip()`. `"Buenos días"`, `"buenos dias"` y `"  BUENOS   DÍAS "` coinciden.
- Token **`{hora:<zona IANA>}`** → hora actual `HH:MM` de esa zona (respeta horario de verano). Zona inválida: se deja el token y se avisa en el log; **nunca rompe la respuesta**.
- Overrides con clave o valor vacío, o no-texto, se **rechazan con aviso** y no impiden arrancar.

### 4.6 Transversal

- **Admin:** el usuario cuyo id sea `NEKITA_MASTER_ID`; se compara el id del **usuario**, nunca del chat. Un valor no numérico se **ignora con aviso** (admin deshabilitado) y no impide arrancar. Intento de un no-admin: `Este comando es solo para el administrador-nya.`
- **Errores en un comando:** se registra con un código corto (3 bytes hex, p. ej. `a3f09c`) y se responde `Algo ha fallado-nya (ref. a3f09c)`. Si ni eso se puede enviar, se registra y no se propaga.
- **Estadísticas:** contador por comando. 🆕 Se separan **comandos usados** y **poles concedidas** (antes se sumaban en "Comandos registrados").
- **`/stats` (admin):** versión, grupos con actividad, comandos usados, poles concedidas y top-10 de comandos.
- **Privacidad:** por defecto **no se registra el texto** de los mensajes; solo con `NEKITA_LOG_MESSAGES=true` y nivel `DEBUG`.
- **Modo de privacidad de Telegram:** por defecto el bot en grupos solo ve comandos y menciones; para que vea "oro", "Hora china"… hay que **desactivar *Group Privacy*** en @BotFather o hacerlo administrador. 🆕 Al arrancar, si `getMe().can_read_all_group_messages` es `false`, se avisa en el log. Se documenta en el README.
- **Apagado limpio:** con SIGTERM/SIGINT se detiene el polling, se esperan los manejadores en curso (con tope) y se cierra la base de datos.
- **Fallo de polling irrecuperable** (token revocado, 409 por otra instancia): el proceso **termina con código ≠ 0** para que systemd lo reinicie; nunca "vivo pero sordo".

### 4.7 Anuncios del administrador

Feature `anuncios` (solo `NEKITA_MASTER_ID`, solo por **chat privado** con el bot):

| Comando | Qué hace |
|---|---|
| `/grupos` | Lista numerada de los grupos activos |
| `/anuncio <texto>` | Anuncio a **todos** los grupos activos |
| `/anuncio_a <nº o id> [...] <texto>` | Anuncio a grupos concretos (nº de `/grupos` o id de chat) |

- **Responder a un mensaje** con el comando lo **copia** tal cual (foto, formato, enlaces) en vez de usar texto.
- **Siempre hay confirmación:** vista previa y botones ✅ Enviar / ❌ Cancelar. Caduca a los 5 min, se usa una sola vez y solo vale para quien lo preparó.
- **Envío con ritmo** (≈15 msg/s, `core/broadcast.py`). Un fallo no detiene al resto. Si expulsaron al bot, el grupo se marca inactivo; si migró a supergrupo, se actualiza el id.
- Al terminar llega un **informe** (enviados / fallidos con motivo) y queda registrado en la tabla `announcements`.
- Los grupos se registran al ver actividad o al añadir al bot (`core/chat_tracking.py`); Telegram no permite listar los grupos del bot. Los grupos que ya existían antes de esta versión aparecen cuando escriben algo.


---
## 5. Arquitectura

Un **monolito modular** en un solo proceso. Reglas de dependencia (se hacen
cumplir con `ruff` `TID` y un test, Fase 0):

```
features/*  ──►  core/*          (nunca al revés)
features/A  ──✗  features/B      (se comunican por servicios del core o por la BD)
```

### 5.1 Estructura de carpetas

```
nekita/
├── pyproject.toml            uv.lock
├── .env.example              README.md   LICENSE   CHANGELOG.md
├── DOCS/                     ESPECIFICACION.md (este fichero), ADR/ (decisiones)
├── deploy/                   nekita.service, nekita-backup.*, logrotate, install.sh
├── migrations/               0001_inicial.sql, 0002_...sql
├── src/nekita/
│   ├── __main__.py           arranque: `python -m nekita`
│   ├── app.py                run(): orquesta arranque/parada con asyncio (5.2)
│   ├── config.py             Settings (pydantic-settings), validado una vez
│   ├── core/
│   │   ├── bot.py            Bot + Dispatcher + registro de features
│   │   ├── feature.py        contrato Feature / Command (6.1)
│   │   ├── registry.py       comandos descubiertos, /help, setMyCommands
│   │   ├── middlewares.py    serialización por chat, usuario, stats, errores
│   │   ├── errors.py         respuesta "Algo ha fallado-nya (ref. …)"
│   │   ├── db.py             conexión SQLite, PRAGMAs, transacciones, migraciones
│   │   ├── scheduler.py      tareas periódicas (asyncio + zoneinfo)
│   │   ├── http.py           AsyncClient compartido + descarga segura
│   │   ├── timeutil.py       día local por zona, franjas, formatos
│   │   └── texts.py          normalización de texto, formateo de nombres
│   └── features/
│       ├── start/   (start, hola, help)
│       ├── info/    (hora, dia, id)
│       ├── images/  (neko, perro, cangrejo, moneda) + providers/ + cache
│       ├── pole/    (service, repo, router, ranking, games.py, games.toml)
│       ├── nekomando/ (service, router, data/nekomandos.json)
│       ├── meta/    (health, stats)
│       └── ia/      (Fase 8) cliente de IA remota detrás de una interfaz
└── tests/
    ├── unit/   integration/ (Telegram falso + BD en memoria)   live/
    └── conftest.py
```

Cada `feature/` sigue la misma forma: `__init__.py` (expone `feature`),
`router.py` (handlers aiogram), `service.py` (lógica pura, sin aiogram),
`repo.py` (SQL, solo si guarda datos). **La lógica vive en `service.py` y se
prueba sin Telegram.**

### 5.2 Ciclo de vida (`app.py`, asyncio puro)

Arranque, en este orden (si algo falla → mensaje claro y `exit 1`):
1. Cargar y validar `Settings` (una vez).
2. Abrir SQLite, aplicar PRAGMAs, **migrar**, importar datos antiguos si procede (7.6).
3. Crear el `AsyncClient` HTTP compartido.
4. Crear `Bot`, registrar features, `getMe` (+ aviso de *Group Privacy*), `setMyCommands`.
5. Lanzar el scheduler y la tarea de **polling** (con vigilancia: si termina con error, se cierra el proceso con código ≠ 0).
6. `app.py` espera a la señal de parada o a la caída del polling (sin servidor HTTP). Si hay `WatchdogSec`, notifica a systemd (5.3).

Parada (SIGTERM): parar polling → esperar manejadores en curso (tope 10 s) →
parar scheduler → cerrar HTTP → `PRAGMA optimize` y cerrar SQLite.

### 5.3 Salud (sin servidor HTTP)

- **No hay puertos abiertos.** Superficie de ataque cero y nada que mantener.
- **Vivo = el proceso corre.** `systemd` con `Restart=on-failure`; cualquier fallo irrecuperable sale con código ≠ 0 (4.6), así que nunca queda "vivo pero sordo".
- **Comprobación funcional:** el comando de Telegram `/health` (4.1).
- **Latido del polling:** marca de tiempo en memoria que actualiza el bucle de polling. Opcional (Fase 8): `WatchdogSec` + `sd_notify` escribiendo en el socket `NOTIFY_SOCKET` (stdlib, sin dependencias) solo mientras el latido sea reciente; si se cuelga, systemd reinicia.
- Si algún día hace falta HTTP (panel, webhook), es una feature de la Fase 8 con autenticación obligatoria.

---

## 6. Cómo añadir funciones (extensibilidad)

### 6.1 Contrato

Una *feature* es un objeto con un `aiogram.Router` y metadatos:

```python
# features/ejemplo/__init__.py  (ilustrativo, NO es código a implementar tal cual)
feature = Feature(
    name="ejemplo",
    router=router,  # handlers de la carpeta
    commands=[CommandInfo("ejemplo", "Hace algo", category="otros", admin_only=False)],
    migrations=None,  # opcional: carpeta propia de SQL
    on_startup=None,
    on_shutdown=None,  # ganchos opcionales
    jobs=[],  # tareas periódicas opcionales
)
```

El núcleo **descubre** todas las carpetas de `features/` (lista explícita en
`features/__init__.py` en vez de importación mágica: más legible y mypy la
entiende). Con eso, `/help`, el menú de Telegram, las estadísticas y el control
de admin funcionan **sin tocar nada más**.

**Comandos generados desde datos:** `commands` es una lista que se construye al
crear la feature, así que una feature puede leer su fichero de datos antes y
generar un `CommandInfo` por entrada. Lo usa `pole` (un comando por pole de
`games.toml`, 4.3). El router recibe esos comandos con un filtro construido
igual. Se valida con un test en la Fase 2 (la receta 6.3 no depende de esto).

### 6.2 Metadatos de comando (🔎 equivalente a `@Command()` de Node)

`name`, `description`, `category`, `admin_only`. Se guardan como `flags` del
handler de aiogram para que los middlewares los lean (admin, estadísticas).

### 6.3 Receta "añadir `/dado`" (criterio de diseño medible)

1. Crear `features/dado/` con `router.py`, `service.py` y `__init__.py`.
2. Añadir **una línea** a `features/__init__.py`.
3. Escribir `tests/unit/test_dado.py`.

Sin editar `/help`, ni el menú, ni estadísticas, ni la configuración del
núcleo. **Criterio de aceptación de la Fase 3:** un test que añade una feature
de juguete y comprueba que aparece en `/help`, en `setMyCommands` y en
`/stats`.

### 6.4 Ampliaciones previstas (no se construyen ahora)

| Idea | Dónde encaja | Requiere |
|---|---|---|
| Recordatorios de usuario | `features/recordatorios/` + tabla propia + `jobs` | Mini-planificador o APScheduler |
| **IA remota (prevista)** | `features/ia/` con proveedor detrás de una interfaz (6.5) | ADR previo; reglas de 6.5 |
| Avisos proactivos de poles | `jobs` de la feature `pole` (una tarea por pole) | Decisión 15; con ≥3 tareas, valorar APScheduler |
| Panel de administración | Servidor HTTP propio en `features/admin/` (reintroduce FastAPI o `aiohttp`) | Autenticación obligatoria; decisión 17 |
| Webhook | Cambiar el modo de recepción en `core/bot.py` | Dominio + HTTPS |
| Límite de uso por usuario | Middleware en `core/` | Tabla o contador en memoria |

### 6.5 IA remota (prevista, Fase 8)

El modelo **no corre en este servidor**: corre en otro PC (Ollama, llama.cpp,
vLLM…) accesible por VPN (Tailscale/WireGuard) o en una API en la nube. Para
el bot es **un cliente HTTP saliente** con `httpx` (ya en el stack), contra un
endpoint compatible con OpenAI. Sin torch ni modelos en el servidor: RAM y
disco casi no cambian.

Reglas de diseño:
1. **Fuera del lock por chat.** La serialización por `chat_id` (sección 3) existe para el orden de las poles; una llamada a la IA (10–30 s) no debe bloquearla. El handler de IA responde en una tarea aparte.
2. **El otro PC estará apagado a veces:** timeout corto, semáforo de concurrencia, límite por usuario y mensaje de fallo (`Ahora mismo no puedo pensar-nya`). Mismo patrón que las imágenes.
3. **Privacidad:** se envía solo lo necesario (mensajes que mencionan al bot o un comando explícito), nunca el chat entero; sin guardar el contenido por defecto.
4. **Interfaz de proveedor** (`complete(messages) -> str`) para cambiar de Ollama a nube sin tocar la feature.
5. Configuración: `NEKITA_AI_URL`, `NEKITA_AI_MODEL`, `NEKITA_AI_KEY`, `NEKITA_AI_TIMEOUT` (sección 8). Si `NEKITA_AI_URL` está vacío, la feature **no se registra**.
6. Seguridad de red: el destino es una URL **de confianza configurada por el admin** (excepción explícita a la regla SSRF de la sección 9, que sigue aplicando a las descargas de imagen); la VPN no expone nada del servidor hacia fuera.

---
## 7. Datos (SQLite)

### 7.1 Ubicación y PRAGMAs

- Fichero: `${NEKITA_DATA_DIR}/nekita.db` (por defecto `~/.nekita/data/`, el mismo directorio que la versión Node; `NEKITA_DATA_DIR` lo cambia).
- Al abrir la conexión: `journal_mode=WAL`, `synchronous=NORMAL` (con WAL no se pierden commits ante un fallo del proceso; ante un corte de luz puede perderse la última transacción, aceptable aquí), `foreign_keys=ON`, `busy_timeout=5000`, `cache_size` pequeño (≈ 2 MB) y `temp_store=MEMORY`.
- **Una única conexión** compartida (un solo proceso, escritor único). Las escrituras son transacciones cortas con `BEGIN IMMEDIATE`.
- ⚠️ Con WAL el directorio debe ser un disco local (no NFS).

### 7.2 Esquema inicial (`0001_inicial.sql`)

Propuesta; se ajusta en la Fase 1. Tablas `STRICT` (ver sección 2 si SQLite < 3.37).

```sql
CREATE TABLE chats (            -- grupo que alguna vez generó actividad
  chat_id     INTEGER PRIMARY KEY,
  title       TEXT,
  first_seen  TEXT NOT NULL,    -- ISO-8601 UTC
  last_seen   TEXT NOT NULL
) STRICT;

CREATE TABLE users (            -- el nombre visible es solo para mostrar
  user_id     INTEGER PRIMARY KEY,
  display     TEXT NOT NULL,
  updated_at  TEXT NOT NULL
) STRICT;

CREATE TABLE pole_wins (        -- una fila por puesto ganado: fuente de verdad
  chat_id   INTEGER NOT NULL REFERENCES chats(chat_id),
  game_id   TEXT    NOT NULL,   -- 'pole', 'canaria', 'patitos' (id de games.toml)
  day_key   TEXT    NOT NULL,   -- 'YYYY-MM-DD' local en la zona de ese juego
  position  INTEGER NOT NULL CHECK (position >= 0),
  user_id   INTEGER NOT NULL REFERENCES users(user_id),
  points    INTEGER NOT NULL CHECK (points >= 0),   -- los de ese momento
  won_at    TEXT    NOT NULL,   -- instante UTC del mensaje
  PRIMARY KEY (chat_id, game_id, day_key, position),
  UNIQUE      (chat_id, game_id, day_key, user_id)
) STRICT;
CREATE INDEX ix_pole_wins_ranking ON pole_wins (chat_id, game_id, user_id);

CREATE TABLE pole_legacy (      -- puntos de Node v1 (por nombre) sin reclamar
  chat_id  INTEGER NOT NULL REFERENCES chats(chat_id),
  game_id  TEXT    NOT NULL,
  name     TEXT    NOT NULL,
  points   INTEGER NOT NULL CHECK (points >= 0),
  PRIMARY KEY (chat_id, game_id, name)
) STRICT;

CREATE TABLE pole_adjust (      -- puntos importados o reclamados del legado
  chat_id  INTEGER NOT NULL REFERENCES chats(chat_id),
  game_id  TEXT    NOT NULL,
  user_id  INTEGER NOT NULL REFERENCES users(user_id),
  points   INTEGER NOT NULL,
  PRIMARY KEY (chat_id, game_id, user_id)
) STRICT;

CREATE TABLE stats (            -- solo contadores de comandos: 'cmd:neko'
  key    TEXT PRIMARY KEY,
  count  INTEGER NOT NULL DEFAULT 0
) STRICT;

CREATE TABLE nekomando_overrides (   -- editables en caliente (opcional, Fase 4)
  phrase    TEXT PRIMARY KEY,        -- ya normalizada
  response  TEXT NOT NULL
) STRICT;
```

Desaparece el estado en memoria `winners`/`nextPosition`: se **deriva** de las filas de `pole_wins` del día. La definición de las poles (`games.toml`) se carga **una vez** al arrancar y se indexa en un diccionario `palabra normalizada → (pole, puesto)`.

### 7.3 Poles en SQL (atómicas y sin cron)

Para un mensaje de grupo con `user_id` y `chat_id`:

1. Normalizar el texto y buscarlo en el diccionario. Sin coincidencia → fuera (sigue a nekomandos).
2. `local` = `message.date` convertido a la zona de la pole. Con `window` y `local` fuera de la franja → no concede.
3. `day_key` = fecha de `local`.
4. En **una transacción** (`BEGIN IMMEDIATE`):
   1. `n` = nº de filas de `pole_wins` de `(chat, pole, day_key)`. Si `n` ≠ puesto de la palabra → `ROLLBACK`, no concede.
   2. `INSERT OR IGNORE` en `chats`; `UPSERT` en `users` (nombre actual).
   3. `INSERT` en `pole_wins` con los **puntos de ese puesto**. Si viola `UNIQUE(chat, pole, day, user)` (ya ganó hoy) o la clave primaria (otro se adelantó) → `ROLLBACK`, no concede. **La restricción de la BD es la garantía**, no el código.
   4. Reclamar legado: si hay `pole_legacy(chat, pole, name)` con su nombre, mover los puntos a `pole_adjust` y borrar la fila.
5. Responder con el `prize` del puesto.

**Ranking** (top 10 de `(chat, pole)`): por `user_id`, suma de `points` de `pole_wins` + `pole_adjust`, unido a `users.display`; más las filas de `pole_legacy` (por nombre). `ORDER BY puntos DESC, display COLLATE NOCASE ASC, user_id ASC LIMIT 10`. **Desempate** (✅ confirmado): a igual puntuación, **alfabético por nombre** sin distinguir mayúsculas; si el nombre también coincide, por `user_id` para que el orden sea siempre el mismo. ⚠️ `NOCASE` de SQLite solo ignora mayúsculas **ASCII**. ✅ Comprobado con `sqlite3` de esta máquina: con 5 puntos cada uno, `Ana`/`ana`/`zoe` salen en ese orden y `Álvaro`/`álvaro` salen **después de `zoe`** (los nombres que empiezan por letra con acento o no latina van al final entre empatados). Alternativa si molesta: ordenar en Python con `str.casefold()` tras leer solo 10 filas empatadas. Se deja como mejora opcional. Los empatados **no comparten** número de puesto (salen como 🥇 🥈 🥉 y `#4`… seguidos).

🆕 Como cada victoria es una fila con fecha y puntos, quedan gratis el histórico por día, "ganadores de ayer", estadísticas por mes y deshacer la **última** victoria de un día.

**Aceptación (tests)**
- (a) **Independencia:** ganar `pole` no afecta a `canaria` ni a `patitos`; ni un grupo a otro; la misma persona puede ganar en dos poles el mismo día.
- (b) **Zonas:** a las 00:30 de Madrid, `pole` ya es del día nuevo y `canaria` sigue en el anterior; a las 01:00:01 de Madrid cambian las dos.
- (c) **Franja:** `patitos` a 22:21:59 no, 22:22:00 sí, 22:22:59 sí, 22:23:00 no.
- (d) **Orden y puestos:** `plata` antes que `oro` no cuenta; `pole` (alternativa) cuenta como oro; en `canaria` un segundo `pole canaria` no concede; una persona no gana dos puestos el mismo día en la misma pole.
- (e) **Acumulado:** puntos de varios días suman; cambiar los `points` del fichero no cambia los ya ganados.
- (f) **Reinicio:** ganar a las 20:00, "reiniciar" a las 23:30 → sigue sin poder ganar el mismo puesto; al día siguiente sí. Bot parado en el cambio de día → el primer mensaje nuevo cuenta para el día nuevo.
- (g) **Concurrencia:** 50 "oro" simultáneos → exactamente 1 oro.
- (h) **Cambios de hora** de marzo y octubre; suite con `TZ=UTC` y `TZ=Europe/Madrid`.
- (i) **Configuración:** palabra repetida entre poles, zona o franja inválidas, comando repetido → el arranque falla con mensaje legible.
- (j) **Ranking:** top 10 con empates (orden alfabético, estable entre llamadas), con más de 10 participantes y con legado sin reclamar.
- (k) **Alias:** una pole de prueba con `words = ["plata", "segundo"]` concede el mismo puesto con cualquiera de las dos; con mayúsculas y espacios sobrantes también; y un alias que ya usa otra pole (o que normalizado coincide) hace fallar el arranque.

---
### 7.4 Estadísticas

`stats(key,count)` con `INSERT … ON CONFLICT DO UPDATE SET count=count+1`. Para no escribir en disco por **cada** comando, los contadores se acumulan en memoria y se vuelcan cada 30 s y al parar (pérdida máxima aceptable: 30 s de contadores). **Los puntos de pole nunca pasan por aquí**: van directos a SQL en la misma transacción que la victoria.

Claves: solo `cmd:<comando>`. 🆕 "Poles concedidas" de `/stats` **no** es un contador aparte: es `COUNT(*)` de `pole_wins`, así que no puede desfasarse de los puntos.

### 7.5 Nekomandos

Los **defaults** viven en `features/nekomando/data/nekomandos.json` (versionado, Apéndice B). Los **overrides** se leen de la tabla `nekomando_overrides` y, por compatibilidad 🔎, también de `~/.nekita/data/nekomandos.json` (`{"overrides": {...}}`) si existe: se importan a la tabla en el primer arranque y el fichero se renombra a `.importado`. Un comando de admin para editarlos es opcional (Fase 8).

### 7.6 Importación desde Node (una sola vez)

El fichero de Node (`grupos_pole.json`) 🔎 tiene esta forma:

```json
{ "chats": { "<chatId>": {
    "schemaVersion": 2,
    "winners": [123, 456],
    "scores":  { "123": 7 },
    "names":   { "123": "fulano" },
    "legacyScores": { "mengano": 4 },
    "nextPosition": 2 } },
  "stats": { "neko": 12, "pole:oro": 3 } }
```

- Todo lo de Node era **una sola pole**: se importa a la pole `pole` (`game_id='pole'`). Las demás empiezan a cero.
- **v1** (sin `schemaVersion`): `scores` está indexado por **nombre** → va a `pole_legacy`.
- **v2:** `scores` por `userId` → `pole_adjust` (+ `users` desde `names`); `legacyScores` → `pole_legacy`. `winners` y `nextPosition` **se descartan** (son estado de un día ya caducado).
- `stats`: las claves `pole:*` **se descartan** (el contador de poles ahora sale de `pole_wins`, y las victorias antiguas no están como filas); el resto se importa como `cmd:<clave>`.
- **Idempotente:** solo se ejecuta si la BD es nueva (`PRAGMA user_version` = 0) **y** existe el fichero; después se renombra a `grupos_pole.json.importado`. Antes se **copia** siempre a `backups/`.
- Un fichero corrupto **no tumba el arranque**: se aparta como `.corrupto`, se avisa y se empieza vacío.
- ✅ **Dato real en esta máquina:** el `grupos_pole.json` de desarrollo está **vacío** (`{"chats": {}, "stats": {}}`), así que aquí no hay nada que migrar. ⚠️ La máquina de producción puede ser otra: se revisa allí antes de desplegar.
- **Aceptación:** tests con ficheros v1, v2, mezclados, vacíos y corruptos.

### 7.7 Copias de seguridad

- Tarea diaria del scheduler: copia consistente con **`VACUUM INTO`** (o la API de backup de `sqlite3`) a `backups/nekita_AAAA-MM-DDTHH-MM-SS.db`. **Nunca `cp`** del fichero con WAL activo.
- Retención: 7 diarias + 4 semanales. ⚠️ Tamaño esperado de la BD < 5 MB (estimación sin medir; con cientos de grupos seguiría siendo pequeña).
- `PRAGMA integrity_check` semanal y siempre antes de restaurar.
- **Restaurar** = parar el servicio, copiar la copia sobre `nekita.db`, borrar `-wal`/`-shm`, arrancar. Se documenta y se **prueba** en la Fase 6.
- Una copia fuera de la máquina (otro disco o remoto) queda como recomendación, no como requisito.

---

## 8. Configuración

Variables de entorno (`.env` en desarrollo; `EnvironmentFile` en systemd).
Se validan **una sola vez** al arrancar: un error se muestra legible y sale con código 1.

| Variable | Obligatoria | Por defecto | Notas |
|---|---|---|---|
| `NEKITA_TOKEN` | **sí** | — | Token de @BotFather. Nunca se registra en logs |
| `NEKITA_MASTER_ID` | no | — | Id numérico del admin; no numérico → aviso y se ignora |
| `NEKITA_TZ` | no | `Europe/Madrid` | Zona IANA válida |
| `NEKITA_CACHE_SEGUNDOS` | no | `300` | TTL de los lotes de imágenes |
| `NEKITA_DATA_DIR` | no | `~/.nekita/data` | BD, copias, overrides |
| `NEKITA_AI_URL` | no | — | (Fase 8) URL base del endpoint de IA remota; vacío = feature desactivada |
| `NEKITA_AI_MODEL` | no | — | (Fase 8) Nombre del modelo |
| `NEKITA_AI_KEY` | no | — | (Fase 8) Clave de la API si la hay; nunca se registra en logs |
| `NEKITA_AI_TIMEOUT` | no | `20` | (Fase 8) Segundos máximos por petición |
| `NEKITA_LOG_LEVEL` | no | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `NEKITA_LOG_MESSAGES` | no | `false` | Registrar el texto de los mensajes (solo con `DEBUG`) |
| `NEKITA_BACKUP_HORA` | no | `04:00` | Hora local de la copia diaria |
| `NEKITA_MAX_HANDLERS` | no | `20` | Handlers simultáneos máximos (9.1) |
| `NEKITA_BACKUP_COPIA_CMD` | no | — | Comando opcional para copiar cada backup fuera del servidor (p. ej. `rsync`/`rclone`) |

**Cambios respecto a Node:** se retiran `NEKITA_HORA_GUARDADO*` (ya no hay
guardado diario) y `NEKITA_HORA_LIMPIEZA*` (el reset a las 22:59) **desaparece**:
el día de cada pole lo define su zona en `games.toml` (4.3). `NEKITA_TZ` queda
solo para `/hora`, `/dia`, nekomandos y copias. Se documenta en el README.
`.env.example` incluye **todas** las variables, **sin comentar**, con valores
vacíos o seguros (🔎 en Node estaban comentadas y `cp .env.example .env` no
daba una configuración usable).

---
## 9. Robustez y seguridad

| Tema | Requisito |
|---|---|
| Secretos | El token solo en `.env`/`EnvironmentFile` con permisos `600`; `.env` en `.gitignore`; filtro de logs que enmascara cualquier cadena con forma de token (`\d+:[A-Za-z0-9_-]{30,}`). CI con escaneo de secretos (`gitleaks`) |
| Admin | Solo por `user.id` de `NEKITA_MASTER_ID`, nunca por chat ni por nombre |
| Entradas | Todo texto de usuario se trata como dato: SQL **siempre parametrizado**; nunca `f"...{texto}..."` en una consulta. Los nombres se envían **sin `parse_mode`** (o escapados) para que un alias con `<`/`*` no rompa ni inyecte formato |
| SSRF | Las descargas de imagen solo admiten `https` y los **dominios de cada proveedor**; se rechazan IPs, `localhost` y redirecciones a otros dominios |
| Recursos | Timeouts en toda llamada externa (10 s API, 15 s descarga); descarga en streaming con tope 10 MB; máx. 2 descargas simultáneas; caché de lotes acotada (nº de claves fijo) |
| Límite de uso | 🆕 Limitador por usuario para comandos de imagen (p. ej. 1 cada 3 s por usuario y chat, en memoria). Evita gastar cuota de APIs externas |
| Errores | Un fallo en un handler **nunca** tumba el bot: se registra con código corto y se responde `Algo ha fallado-nya (ref. …)` |
| Apagado | Señales manejadas; exit 0 en parada limpia, ≠ 0 en fallo irrecuperable |
| Telegram | Respeta `RetryAfter` (429): espera lo indicado y reintenta una vez; `Forbidden` (bot expulsado del grupo) se registra a nivel `INFO` y no es un error |
| Dependencias | `uv.lock` versionado; `pip-audit` en CI y semanal; Dependabot o Renovate para `uv`/`github-actions` |

### 9.1 Colas y límites (todo en memoria, sin Redis/Celery)

Con 1 core y una sola instancia, `asyncio` ya es la cola. Se usan solo estas piezas:

| Pieza | Para qué | Valor |
|---|---|---|
| Lock por `chat_id` | Orden de poles ("oro" → "plata") | 1 por chat, limpieza de inactivos |
| Semáforo global de handlers | *Backpressure*: tras una caída llegan updates acumulados de golpe; evita picos de RAM | `NEKITA_MAX_HANDLERS` = 20 |
| Descarte de updates antiguos | No responder a un `/neko` de hace 10 min | > 60 s y no es pole → se ignora |
| Semáforo de descargas | Memoria al bajar imágenes | 2 |
| Semáforo de IA | El PC remoto no se satura (6.5) | 1–2 con tope de espera |
| Limitador por usuario | Cuota de APIs externas | 1 cada 3 s |
| Escrituras SQLite | Un solo escritor: WAL + `busy_timeout` + una conexión `aiosqlite` (cola natural) | Test de 50 "oro" a la vez |
| **Cola de salida con ritmo** | Solo si se aprueba la decisión 15 (avisos a muchos grupos): ~1 msg/s por chat y ~30/s global (⚠️ cifras de memoria, verificar) | Condicional; hasta entonces basta `RetryAfter` (sección 9) |

**Idempotencia:** tras un reinicio Telegram puede reenviar el último update; la
pole es atómica en SQL (7.3), así que no se concede dos veces.

## 10. Observabilidad

- **Logs** a stdout en formato de texto legible (`journalctl` los recoge); con `NEKITA_LOG_LEVEL=DEBUG` se ven detalles. Cada línea de error con código de referencia.
- Mismo nivel configurable para `aiogram` y `httpx`; `httpx` en `WARNING` salvo `DEBUG` (si no, imprime URLs con parámetros).
- `journald` limita su tamaño (`SystemMaxUse=200M` recomendado) para proteger los 8 GB.
- **Salud:** sin puertos; `Restart=on-failure` de systemd, comando `/health` de Telegram y `WatchdogSec` opcional (5.3, Fase 8).
- **Sin métricas externas** por ahora: `/stats` cubre el uso funcional; RSS y CPU se miran con `systemctl status`/`journalctl`.

---

## 11. Estrategia de pruebas

Objetivo: lo que une las piezas es donde aparecieron los bugs reales en Node
(🔎 cobertura 62 % con la lógica pura al 90–100 % y el "pegamento" al 0 %).
Aquí **el pegamento se prueba desde el principio**.

| Nivel | Qué | Cómo |
|---|---|---|
| Unitario | `service.py` puro: normalización, día local y franja, caché, selección de puesto, formateo | `pytest`, sin red ni BD |
| Repo | SQL real | SQLite **en memoria** con las migraciones reales (no mocks) |
| Integración (el más valioso) | Flujo completo Telegram→handler→respuesta | `Bot` real de aiogram con una **sesión falsa** (`BaseSession` propia) que registra cada método enviado; se alimenta con `dp.feed_update(bot, Update(...))` y una BD en memoria |
| Tiempo | Jornadas, cambios de hora, medianoche, reinicio | Reloj inyectado (función `now()` en el servicio), **no** parches globales; suite con `TZ=UTC` y `TZ=Europe/Madrid` |
| Concurrencia | 50 "oro" a la vez; orden "oro"→"plata" seguidos | `asyncio.gather` sobre el flujo de integración |
| Arranque | Sin token → mensaje legible y `exit 1`; con token falso → intenta conectar y cierra limpio con SIGTERM | Subproceso real |
| Contrato *live* | TheCatAPI, random.dog, generatorfun y Wikimedia devuelven URL de imagen válida | `pytest -m live`, **fuera** de la CI normal, job nocturno |

**Flujos obligatorios del test de integración:** comando válido; comando de
admin con y sin permiso; "oro/plata/bronce" en grupo y en privado; texto libre
de nekomando; mensaje sin handler; error forzado en un comando (ref. en la
respuesta); `/help` según rol; `/start@OtroBot` ignorado; menú `setMyCommands`
sin los de admin; descarga plan B y plan C.

**Reglas:** un test de regresión por cada bug conocido, **rojo antes del
arreglo**; sin `sleep` real; sin red en tests normales (`pytest` falla si
alguien abre un socket); `filterwarnings=error`. **Umbral de cobertura:**
≥ 85 % global y ≥ 95 % en `pole/` y `core/timeutil.py` (⚠️ cifras propuestas,
se ajustan tras la Fase 3).

## 12. Despliegue (Debian + systemd)

- Usuario de sistema `nekita` sin shell; código y venv en `/opt/nekita`; datos en `/var/lib/nekita` (`NEKITA_DATA_DIR`); `.env` en `/etc/nekita/nekita.env` (`600`, dueño `nekita`).
- Instalación: `uv sync --frozen --no-dev` (⚠️ si `uv` no está disponible en el servidor: `python3 -m venv` + `pip install` de un `requirements.txt` exportado con `uv export`).
- Unidad `nekita.service` con `Restart=on-failure`, `RestartSec=5`, `MemoryMax=400M`, `NoNewPrivileges=true`, `ProtectSystem=strict`, `ReadWritePaths=/var/lib/nekita`, `PrivateTmp=true`, `ProtectHome=true`.
- `nekita-backup.timer` solo si se prefiere desacoplar la copia del proceso; por defecto la hace el scheduler interno (7.7).
- **Actualizar:** `git pull` → `uv sync --frozen --no-dev` → `systemctl restart nekita` (las migraciones corren solas al arrancar y son **hacia delante**; antes de migrar se hace copia automática).
- **Docker: no se usa en producción** (el motor y la imagen restan cientos de MB de los 8 GB y añaden un demonio en 1 GB de RAM; el sandbox de systemd basta). Opcional: `python:3.13-slim`, usuario no root, `mem_limit`, volumen de datos; solo si lo pides.
- **Redis, ORM y colas: no** (una instancia, un SQLite local).
- **Retirar la versión Node:** parar el servicio/contenedor anterior **antes** de arrancar este (un mismo token no admite dos `getUpdates`: error 409).

---
## 13. Fases de implementación

Cada fase termina con **algo que funciona y se puede probar**, y deja la rama
en verde (`ruff`, `mypy --strict`, `pytest`). Cada una tiene **Entregables**,
**Hecho cuando** (criterios medibles) y **Riesgos**. No se empieza una fase con
la anterior en rojo.

| Fase | Nombre | Resultado visible | Depende de |
|---|---|---|---|
| 0 | Cimientos | Proyecto, calidad y CI en verde; arranca y se para limpio; medición de RAM/disco en el servidor real | — |
| 1 | Núcleo de datos | BD + migraciones + copias + importador de Node | 0 |
| 2 | Núcleo del bot | Bot arranca, polling, errores, admin; `/help` y menú automáticos | 0, 1 |
| 3 | Funciones sencillas | `/start /hola /hora /dia /id /health /stats` + feature de juguete | 2 |
| 4 | Nekomandos | Frases libres con overrides | 2 |
| 5 | Poles | Varias poles independientes por datos, atómicas y sin cron | 1, 2 |
| 6 | Imágenes | `/neko /perro /cangrejo /moneda` con caché y plan B | 2 |
| 7 | Operación | systemd, copias, restauración, medición, prueba real | 1–6 |
| 8 | Extras (opcional) | **IA remota (prevista)**, avisos de poles, `WatchdogSec`, webhook, panel… | 7 |

### Fase 0 — Cimientos

**Entregables**
- [ ] Rama `python` con `pyproject.toml` (sección 3), `uv.lock`, `.gitignore`, `LICENSE`, `README` mínimo y `.env.example` completo.
- [ ] Estructura de carpetas (5.1) con `__init__.py`; `__main__.py` y `app.py` con el bucle `asyncio` de arranque/parada y manejo de SIGTERM/SIGINT.
- [ ] `config.py` con validación y mensaje legible si falta `NEKITA_TOKEN` (`exit 1`).
- [ ] **Medición en el servidor real:** `python3 --version`, versión de SQLite, instalar dependencias, comprobar `aiosqlite` y medir RSS en reposo y disco del venv (presupuesto de la sección 2).
- [ ] Logging configurable (`NEKITA_LOG_LEVEL`) con enmascarado de token.
- [ ] CI (GitHub Actions): `ruff check`, `ruff format --check`, `mypy`, `pytest --cov`, `pip-audit`, `gitleaks`; solo Python 3.13.
- [ ] Test de la regla de dependencias (`core` no importa `features`; una feature no importa otra).
- [ ] ADR corto `DOCS/ADR/0001`: por qué aiogram + asyncio (sin FastAPI) + SQLite + systemd (sin Docker ni Redis).

**Hecho cuando:** `uv run pytest`, `ruff` y `mypy --strict` pasan en limpio; arrancar sin token da un mensaje claro y código 1; con un token cualquiera el proceso arranca, intenta conectar y con SIGTERM se cierra limpio en < 5 s; se comprobó en el servidor real que `aiosqlite` instala y funciona con 3.13 y se anotó el RSS/disco medidos.

**Riesgos:** `mypy --strict` con aiogram puede pedir ajustes (`# type: ignore` justificados); SQLite del servidor sin `STRICT` (sección 2).

### Fase 1 — Núcleo de datos

**Entregables**
- [ ] `core/db.py`: apertura, PRAGMAs (7.1), transacciones y **ejecutor de migraciones** (`user_version`; cada fichero en una transacción; fallo → aborta el arranque).
- [ ] `migrations/0001_inicial.sql` (7.2).
- [ ] Copia automática **antes** de migrar si ya hay datos.
- [ ] `core/backup.py`: `VACUUM INTO` + retención (7.7) y su test.
- [ ] Importador de Node (7.6) con tests v1, v2, mezclado, vacío y corrupto.
- [ ] Contadores de estadísticas en memoria con volcado periódico (7.4).

**Hecho cuando:** los tests de repo pasan con SQLite en memoria; abrir una BD de versión superior a la conocida **falla con mensaje claro** sin tocarla; importar datos de ejemplo deja los mismos puntos por usuario; matar el proceso a mitad de una escritura deja `integrity_check` en `ok`.

**Riesgos:** corrupción por copiar el fichero con WAL activo (mitigado: solo `VACUUM INTO`); formato real de producción distinto al documentado (importador tolerante; se revisa el fichero real antes de la Fase 7).

### Fase 2 — Núcleo del bot

**Entregables**
- [ ] `core/feature.py` (contrato 6.1) y `features/__init__.py` con la lista explícita.
- [ ] `core/bot.py`: `Bot`, `Dispatcher`, registro de features, `getMe` + aviso de *Group Privacy*, `setMyCommands` (sin admin).
- [ ] Middlewares: usuario/`is_admin`, **serialización por chat**, estadísticas (solo éxito), errores con referencia, filtro `@OtroBot`, limitador de uso.
- [ ] **Colas simples (sin broker externo, 9.1):** semáforo global de handlers (`NEKITA_MAX_HANDLERS`, 20) y descarte de updates de comandos de imagen/IA con más de 60 s de antigüedad (las poles **nunca** se descartan).
- [ ] Guard `admin_only` con el mensaje literal del Apéndice A.
- [ ] Vigilancia del polling: caída irrecuperable → `exit` ≠ 0; el latido del polling queda disponible en memoria (5.3).
- [ ] Parada limpia (5.2).
- [ ] **Sesión falsa de Telegram** y fixtures de integración (sección 11): hace seguras las fases siguientes.

**Hecho cuando:** test de integración con un comando de juguete: responde, cuenta estadística, falla con `ref. xxxxxx` sin caer, el admin pasa y el no admin recibe el rechazo, `/comando@OtroBot` se ignora; test de arranque real con token falso (conecta, falla legible, `exit` ≠ 0; con SIGTERM cierra en < 5 s).

**Riesgos:** updates concurrentes (mitigado con la serialización por chat y un test de orden); cambios entre versiones menores de aiogram (se fija `<4` y se usa el lock).

### Fase 3 — Funciones sencillas

**Entregables**
- [ ] `features/start` (`/start`, `/hola`, `/help` generado), `features/info` (`/hora`, `/dia`, `/id`), `features/meta` (`/health`, `/stats` con comandos y poles separados).
- [ ] `core/timeutil.py`: formatos y zonas, con tests en `TZ=UTC` y `Europe/Madrid`.
- [ ] Descripciones del menú copiadas de la versión anterior (aviso en 4.1).
- [ ] Test de la **receta 6.3**: una feature de juguete aparece sola en `/help`, el menú y `/stats`.

**Hecho cuando:** todos los textos coinciden con el Apéndice A (test con los literales); `/help` no muestra `/stats` a un no admin; `/dia` entre las 00:00 y las 02:00 de España da el día correcto.

---
### Fase 4 — Nekomandos

**Entregables**
- [ ] `features/nekomando` con los datos del Apéndice B, normalización única (4.5) y token `{hora:<zona>}`.
- [ ] Carga de overrides (tabla + importación del `nekomandos.json` de Node) con validación y avisos.
- [ ] `/help` incluye el párrafo de frases libres **generado** desde los datos 🆕 (en Node estaba copiado a mano y se desfasaba).

**Hecho cuando:** tests de normalización (acentos, mayúsculas, espacios), zona inválida (no rompe), override inválido (se rechaza con aviso y el bot arranca) y **orden pole → nekomando** (una frase que sea pole no llega a nekomando).

### Fase 5 — Poles

**Entregables**
- [ ] `core/timeutil.py`: día local por zona y franja `[from,to)` con reloj inyectado.
- [ ] `features/pole/games.py` + `games.toml`: carga con `tomllib`, validación (4.3.1) e índice palabra → (pole, puesto).
- [ ] Las tres poles de partida (`pole`, `canaria`, `patitos`) con los puntos del ejemplo de 4.3 (3/2/1; 1; 1).
- [ ] `features/pole`: repo SQL (7.3), servicio, router (solo grupos) y **un comando de ranking por pole**, registrados desde el fichero (el contrato de feature, 6.1, debe permitir comandos dinámicos: se verifica en la Fase 2).
- [ ] Top 10 por pole y grupo; mensajes literales (Apéndice A).
- [ ] Solo si se aprueba la decisión 15: cola de salida con ritmo y `jobs` por pole (9.1).
- [ ] Reclamación de puntos legado por nombre (pole `pole`).

**Hecho cuando:** pasan los tests (a)–(j) de 7.3; en privado se ignora; el top 10 cabe en 4096 caracteres con nombres largos; cambiar de alias no cambia los puntos; añadir una pole de prueba **solo editando `games.toml`** la hace funcionar con su comando, sin tocar código.

**Riesgos:** el día local en los dos domingos de cambio de hora; la franja de `patitos` depende de que el bot reciba el mensaje a tiempo (con *Group Privacy* activo no lo ve); nombres con caracteres especiales (se envía sin `parse_mode`).

### Fase 6 — Imágenes

**Entregables**
- [ ] `core/http.py`: cliente único, timeouts y **descarga segura** (https, dominios permitidos, streaming, tope, semáforo de 2).
- [ ] Proveedores `cat`, `dog`, `cangrejo`, `moneda` tras una interfaz común (`get_urls() -> list[str]`).
- [ ] Caché de lotes con una URL distinta por petición y relleno con `Lock` por clave (4.4).
- [ ] Envío por extensión, plan B y plan C, con los mensajes del Apéndice A.
- [ ] Tests con `httpx.MockTransport` (sin red) y `tests/live/` con `-m live`.

**Hecho cuando:** 5 `/neko` seguidos dan 5 URLs distintas con 1 sola llamada a la API; 20 peticiones simultáneas con caché vacía hacen **1** llamada; una URL `http://` o de dominio no permitido se rechaza; una descarga de 20 MB se corta en 10 MB; foto rechazada → documento; gif/mp4 usan el método correcto; el job `live` pasa contra las 4 fuentes (⚠️ puede fallar por cambios de terceros: no bloquea la CI normal).

**Riesgos:** fuentes externas que cambian o caen (random.dog y generatorfun no tienen contrato); límites de Telegram (verificar, 4.4).

### Fase 7 — Operación y puesta en marcha

**Entregables**
- [ ] `deploy/nekita.service`, `install.sh` (usuario, carpetas, permisos), tope de `journald` y swap opcional.
- [ ] **Medición real** de RAM/CPU/disco contra el presupuesto de la sección 2, anotada en un ADR.
- [ ] Copia y **restauración probada** (7.7) y procedimiento de actualización.
- [ ] **Copia externa** de los backups (`NEKITA_BACKUP_COPIA_CMD`: otro PC por la VPN, rsync/rclone): `VACUUM INTO` en el mismo disco no protege de un fallo del disco.
- [ ] `unattended-upgrades` activo y reloj sincronizado (`systemd-timesyncd`/`timedatectl`): las poles dependen de la hora.
- [ ] README completo: instalación, *Group Privacy*, variables, equivalencias con Node, problemas frecuentes.
- [ ] Prueba manual con **token real** en un grupo de prueba: todos los comandos, pole completa, reinicio a mitad de día, `kill -9` y arranque. ⚠️ Nada de esto se ha probado nunca contra Telegram real.
- [ ] Importar los datos reales de producción (tras revisar el fichero) y retirar el servicio Node.
- [ ] `CHANGELOG.md` y etiqueta `v2.0.0`.

**Hecho cuando:** RSS en reposo y pico dentro del presupuesto (o ADR que justifica la desviación); `kill -9` seguido de arranque conserva todos los puntos; restaurar una copia funciona; `systemctl restart` tarda < 10 s; no hay mensajes duplicados.

### Fase 8 — Extras (opcional; cada uno requiere decisión)

**IA remota (prevista, 6.5)**, avisos proactivos de poles (decisión 15),
`WatchdogSec`, webhook, panel admin (reintroduciría HTTP), comando de admin
para editar nekomandos, recordatorios, límite de uso persistente, métricas.
Cada uno empieza con un ADR corto (qué, coste en RAM, riesgo) y se construye
**como una feature** (6.1).

---

## 14. Riesgos globales

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Nada probado aún contra Telegram real (el `.env` local solo tiene placeholders) | Alta | Alto | Fase 7 con token real y grupo de prueba; test de integración con sesión falsa desde la Fase 2 |
| RAM > 1 GB con picos de descarga | Baja | Alto | Streaming + tope + semáforo + `MemoryMax` |
| Fuentes de imágenes cambian o caen | Media | Bajo | Plan B, mensajes de "no veo…", tests `live` nocturnos |
| Pérdida de datos por mala restauración | Baja | Alto | `VACUUM INTO`, restauración **probada**, copias semanales |
| Dos instancias con el mismo token (409) | Media | Medio | Parar Node antes; salida ≠ 0 y aviso claro |
| Alcance creciente (IA, panel…) | Media | Medio | Fase 8 fuera del camino crítico; ADR por extra |
| Cambios de API de aiogram | Baja | Medio | `<4`, `uv.lock`, tests de integración |
| aiogram no encaja con 1 GB | Muy baja | Medio | Medición en la **Fase 0** (servidor real) y en la 7 |
| IA remota caída o lenta (PC apagado, VPN caída) | Alta | Bajo | Timeouts, semáforo, mensaje de fallo, fuera del lock por chat (6.5) |

## 15. Fuera de alcance (explícito)

Servidor HTTP/FastAPI, panel web, varios idiomas, webhook, métricas Prometheus,
varias instancias o alta disponibilidad, ORM, Redis/colas, Docker en
producción, y migrar a PostgreSQL. Entran solo a través de la Fase 8. La IA
remota (6.5) está **prevista** en la Fase 8, no excluida.

## 16. Decisiones pendientes de confirmar

Se aplicó la opción marcada ✔ por defecto. **Cambiarlas es barato ahora, caro después de la Fase 2.**

| # | Decisión | Opciones | Aplicada |
|---|---|---|---|
| 1 | Cliente de Telegram | **aiogram** · python-telegram-bot | ✔ aiogram |
| 2 | Recepción | **polling** · webhook | ✔ polling |
| 3 | Despliegue | **systemd** · Docker | ✔ systemd (Docker opcional) |
| 4 | Inicio del día de cada pole | 22:59 · **00:00 en la zona de cada pole** | ✔ 00:00 local de la pole (petición del usuario; sustituye a Node) |
| 5 | Poles sin cron (día calculado) | **sí** · mantener cron | ✔ sí |
| 6 | Importar datos de Node | **sí, una vez** · empezar de cero | ✔ sí |
| 7 | Límite de uso en comandos de imagen | **sí (1 cada 3 s)** · no | ✔ sí |
| 8 | Nombre del fichero BD y ubicación | **`~/.nekita/data/nekita.db`** · `/var/lib/nekita` | ✔ `NEKITA_DATA_DIR` configurable |
| 9 | Licencia | **GPL-3.0** | ✔ sin cambios |
| 10 | Puntos de `canaria` y `patitos` (puesto único) | 3 · **1** | ✔ 1 (confirmado) |
| 11 | Plata/bronce de `pole` con palabras alternativas | **ninguna por ahora, pero preparado** · añadirlas ya | ✔ ninguna; `words` es una lista (4.3, test k) |
| 12 | Desempate en el ranking | **alfabético** · quien llegó antes · compartir puesto | ✔ alfabético (confirmado) |
| 13 | Definir poles | **fichero `games.toml` + reinicio** · comandos desde el chat | ✔ fichero |
| 14 | Poles de los nekomandos (`peninsular`, `andaluza`, `palitos`, `cuack`, `… canarias`) | siguen siendo texto · convertirlas en poles | ⚠️ siguen siendo texto hasta que se definan (4.3.2) |
| 15 | Avisos proactivos de las poles (el bot escribe solo a la hora de cada pole) | **no** · sí (requiere scheduler, `jobs` por pole) | ⚠️ **pendiente**; por defecto no (sin cron, 7.3) |
| 16 | IA | **remota** (PC por VPN o nube), cliente HTTP saliente · local en el servidor | ✔ remota, Fase 8 (6.5) |
| 17 | Servidor HTTP (FastAPI) | **ninguno** · FastAPI para un futuro panel | ✔ ninguno (más ligero; panel = Fase 8) |
| 18 | Redis / Docker en producción | **no / no (systemd)** · sí | ✔ no / no |

---
## Apéndice A — Textos literales (contrato)

Copiados del código Node ✅. Los tests de las fases 3–6 comparan contra estos literales.

| Dónde | Texto |
|---|---|
| `/start` | `Puedo hacer muchas cosas por tu grupo. Soy una sustituta definitiva para que podáis hacer poles, enviar nekos a tu amigo favorito y mucho más. Pregúntame qué puedo hacer con /help` |
| `/hola` | `Hola, <@usuario o nombre>-nya.` |
| `/hora` | `Son las: HH:MM:SS` |
| `/dia` | `Hoy es: DD-MM-YYYY` |
| `/id` | `El ID de este grupo es: <chat_id>` |
| `/health` | `🐱 Nekita está viva! v<versión>` |
| `/help` (cabecera) | `Mis comandos son los siguientes-nya:` + línea en blanco |
| `/help` (por categoría, orden alfabético) | `📋 <categoría>:` y, indentado con 2 espacios, `/<comando> — <descripción>` (ordenados) |
| `/help` (pie) | `¡Y muchos otros comandos más directamente escritos! Como por ejemplo:` + una línea por grupo de frases (ver Apéndice B; 🆕 generado desde los datos) |
| Ranking vacío (cada pole) | `No hay puntuaciones de <title> aún-nya. ¡Sé el primero!` (con `title = pole` es el literal de Node ✅) |
| Ranking, cabecera | `Puntuaciones de <title>-nya!` + línea en blanco; cada fila `<🥇/🥈/🥉/#N> <nombre>: <N> pts`, máx. **10** filas. Con `title = pole`, literal de Node ✅ salvo el tope (Node: 20) |
| Pole ganada | `¡Enhorabuena <nombre>! Has ganado <prize>-nya` con `prize` = `la pole` / `la plata` / `el bronce` ✅ en la pole principal; en las demás, el `prize` de `games.toml` 🆕 |
| Texto de Node sin uso | `Aún no hay puntuaciones registradas-nya. ¡Empieza a participar escribiendo oro, plata o bronce!` (distinguía "sin datos" de "vacío"; aquí no hay esa diferencia) |
| `/stats` | `📊 Estadísticas de Nekita v<versión>-nya!` · `Grupos activos: N` · 🆕 `Comandos usados: N` · 🆕 `Poles concedidas: N` · `Comandos más usados:` + `  • <cmd>: <N>` |
| Sin permiso | `Este comando es solo para el administrador-nya.` |
| Error en comando | `Algo ha fallado-nya (ref. <6 hex>)` |
| `/neko` sin imagen | `Todos los nekos están escondidos-nya` |
| `/perro` sin imagen | `Ahora mismo no veo ningún perrito-nya` |
| `/cangrejo` sin imagen | `Ahora mismo no veo ningún cangrejito-nya` |
| `/moneda` sin imagen | `Ahora mismo no veo ninguna monedita-nya` |
| `/neko` error | `Error obteniendo imagen de gato-nya` |
| `/perro` error | `Error obteniendo imagen de perro-nya` |
| `/cangrejo` error | `Error obteniendo imagen de cangrejo-nya` |
| `/moneda` error | `Error obteniendo imagen de moneda-nya` |

Descripciones del menú de Telegram ✅: `start` Mensaje de bienvenida · `hola` Saluda al usuario · `help` Lista de comandos disponibles · `hora` Hora actual en España · `dia` Fecha actual · `id` ID del chat actual · `neko` Imagen aleatoria de un gato · `perro` Imagen aleatoria de un perro · `cangrejo` Imagen aleatoria de un cangrejo · `moneda` Imagen aleatoria de una moneda · `pole` Leaderboard de pole del grupo · `health` Comprueba que el bot está vivo · `stats` Estadísticas del bot (solo admin, **no se publica**).

> ⚠️ Los textos de las líneas "Comandos usados" y "Poles concedidas" de `/stats` son **nuevos** (🆕), no existían en Node. El resto son literales.

---

## Apéndice B — Nekomandos por defecto (contrato)

Claves ya normalizadas ✅ (`nekomandos.data.ts`). Sustituciones `{hora:<zona>}` en el momento de responder.

| Frase | Respuesta |
|---|---|
| `hora china` | `En China son las: {hora:Asia/Shanghai}` |
| `hora` | `En España (península) son las: {hora:Europe/Madrid}` |
| `hora canaria` | `En Canarias son las: {hora:Atlantic/Canary}` |
| `hora rusa` | `En Rusia (Moscú) son las: {hora:Europe/Moscow}` |
| `hora venezuela` | `Sin comida no hay hora.` |
| `pole canaria` | `A las 12:00 de canarias` |
| `pole peninsular` | `A las 11:00 de canarias` |
| `pole andaluza` | `Hazla cuando quieras, pero a las 06:00 península está bien-nya.` |
| `pole palitos` | `A las 11:11, tú puedes-nya!` |
| `pole patitos` · `pole cuack` · `pole patitos canarias` · `pole cuack canarias` | `A las 22:22, tú puedes-nya!` |
| `dobby` | `Dobby no tiene amo Dobby es un elfo libre` |
| `:)` | `:)` |
| `:(` | `Sonríe, eres especial-nya!!` |
| `:3` | `¯\_(=^･ω･^)_/¯` |
| `plc` | `Eso te lo hago yo con un Arduino de 3 euros.` |
| `buenos dias` | `Buenos días para ti también.` |
| `buenas tardes` | `Buenas tardes, ¿ya has comido-nya?` |
| `buenas noches` | `Buenas noches, que duermas bien-NYA!!` |
| `buenas` · `hola` | `Hola, ¿qué tal?` |

**Párrafo de `/help` en Node** (se genera en la versión nueva, 🆕; ejemplo de salida esperada): `Hora china, Hora, Hora canaria, Hora rusa, Hora venezuela` / `Pole canaria, Pole peninsular, Pole andaluza, Pole palitos, Pole patitos` / `Pole cuack, Dobby, PLC` / `:), :(, :3` / `Buenos días, Buenas tardes, Buenas noches, Buenas, Hola`. Para poder generarlo, cada frase del fichero de datos lleva un campo opcional `grupo` y `etiqueta` (cómo se muestra, p. ej. "Buenos días").

---

## Apéndice C — Origen de esta especificación

| Qué | De dónde |
|---|---|
| Comportamiento y textos | Versión anterior del bot (Node/NestJS), leída del código |
| Formato de datos a importar | `grupos_pole.json` de esa versión (sección 7.6) |
| Versiones de librerías | Resolución real con `uv` en Python 3.13 el 18-10-2026 |

El código anterior ya no forma parte del repositorio; solo se conserva el importador
de sus datos (`core/importer.py`).
