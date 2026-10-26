# 🐱 Nekita

Bot de Telegram ligero (Python 3.13, aiogram, SQLite). Diseño y plan por fases en
[`DOCS/ESPECIFICACION.md`](DOCS/ESPECIFICACION.md).

> Estado: **Fase 0** (cimientos). El bot aún no conecta con Telegram.

## Desarrollo

```bash
uv sync                    # instala dependencias (Python 3.13)
cp .env.example .env       # y rellena NEKITA_TOKEN (de @BotFather)
uv run python -m nekita    # arranca (Ctrl+C o SIGTERM para parar)
uv run pytest              # tests
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

## Telegram: Group Privacy
Para que el bot vea frases libres ("oro", "hora china"…) en grupos hay que
**desactivar *Group Privacy*** en @BotFather (`/setprivacy` → Disable) o hacerlo administrador.

## Licencia
GPL-3.0.
