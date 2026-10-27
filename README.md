# 🐱 Nekita

Bot de Telegram ligero (Python 3.13, aiogram 3, SQLite) para grupos: poles diarias,
imágenes de neko/perro/cangrejo, moneda, hora mundial y respuestas fijas.
Diseño y plan por fases en [`DOCS/ESPECIFICACION.md`](DOCS/ESPECIFICACION.md).

## Puesta en marcha rápida (desarrollo)

1. En @BotFather: `/newbot` y copia el token. **Desactiva Group Privacy**
   (`/setprivacy` → Disable) o el bot no verá "oro" ni los nekomandos en grupos.
2. Clona y arranca:

```bash
git clone https://github.com/Xibhu/Nekita && cd Nekita
uv sync                    # Python 3.13
cp .env.example .env       # pon NEKITA_TOKEN (y NEKITA_MASTER_ID, tu id de usuario)
uv run python -m nekita    # Ctrl+C o SIGTERM para parar
```

La base de datos y las carpetas se crean solas en `~/.nekita/data`.

## Instalación en un servidor Debian (systemd, sin Docker)

```bash
git clone https://github.com/Xibhu/Nekita && cd Nekita
sudo deploy/install.sh              # usuario, /opt/nekita, venv, servicio, journald
sudo nano /etc/nekita/nekita.env    # NEKITA_TOKEN
sudo systemctl enable --now nekita
journalctl -u nekita -f
```

Requiere `python3` >= 3.13, `python3-venv` y SQLite >= 3.37. Datos en `/var/lib/nekita`.
**Actualizar:** `git pull && sudo deploy/install.sh`. Con la versión Node: páralo antes
(un token no admite dos instancias, error 409).

### Copias de seguridad y restauración
Cada día a `NEKITA_BACKUP_HORA` se crea una copia (`VACUUM INTO`, 7 diarias + 4 semanales)
en `backups/`. Para protegerte de un fallo del disco, `NEKITA_BACKUP_COPIA_CMD` copia cada
una fuera, por ejemplo `rsync -a {file} usuario@pc:/backups/nekita/`.

```bash
sudo deploy/restore.sh /var/lib/nekita/backups/nekita_2026-10-27T04-00-00.db
```
Comprueba la copia, para el servicio, aparta la BD actual (no la borra) y arranca.

## Comandos
`/help` los lista todos (se genera solo). Texto libre: poles (`oro`, `plata`, `pole canaria`…)
y nekomandos (`hora china`, `buenos días`…).
Solo admin (`NEKITA_MASTER_ID`; los anuncios, por privado): `/stats`, `/grupos`, `/anuncio`, `/anuncio_a`.

Las poles se definen en `src/nekita/features/pole/games.toml` (palabras, puntos, zona y franja)
y los nekomandos en `src/nekita/features/nekomando/data/nekomandos.json`. Se reinicia para aplicar.

## Variables (`.env`)
| Variable | Por defecto | Para qué |
|---|---|---|
| `NEKITA_TOKEN` | — | Token de @BotFather (obligatorio) |
| `NEKITA_MASTER_ID` | — | Id de usuario del administrador |
| `NEKITA_TZ` | `Europe/Madrid` | Zona por defecto |
| `NEKITA_DATA_DIR` | `~/.nekita/data` | Base de datos y copias |
| `NEKITA_BACKUP_HORA` | `04:00` | Hora de la copia diaria |
| `NEKITA_BACKUP_COPIA_CMD` | vacío | Copia externa de los backups |
| `NEKITA_CACHE_SEGUNDOS` | `300` | Caché de imágenes |
| `NEKITA_MAX_HANDLERS` | `20` | Mensajes procesados a la vez |
| `NEKITA_LOG_LEVEL` | `INFO` | Nivel de log |

## Problemas frecuentes
- **No reacciona a "oro" en grupos:** Group Privacy sigue activado (el log lo avisa al arrancar).
- **`409 Conflict` / sale con error:** otra instancia usa el mismo token (¿la versión Node?).
- **Sale con "token rechazado":** revisa `NEKITA_TOKEN` o regénéralo en @BotFather.
- **Puntos u horas raros:** comprueba el reloj (`timedatectl`); las poles dependen de la hora.
- **"SQLite demasiado antiguo":** hace falta >= 3.37.

## Desarrollo
```bash
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

## Licencia
GPL-3.0.
