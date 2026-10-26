# ADR 0001 — Stack: aiogram + asyncio + SQLite + systemd

**Estado:** aceptado · **Fecha:** 2026-10-26

## Contexto
Servidor con 1 core, 1 GB de RAM y 8 GB de disco (Debian minimal). Bot de Telegram
con polling, varias poles por datos y, más adelante, IA remota.

## Decisión
- **aiogram 3** (routers por feature, middlewares, flags) con long polling.
- **asyncio puro** como punto de entrada; **sin FastAPI/uvicorn**: no hay servidor HTTP
  que mantener ni puertos abiertos. La salud la vigila systemd.
- **SQLite** (aiosqlite) con SQL explícito y migraciones propias; sin ORM.
- **systemd** sin Docker; **sin Redis**: una instancia, las colas son de `asyncio`.
- **IA remota** (Fase 8) como cliente `httpx` saliente; nada pesado en el servidor.

## Consecuencias
- Menos RAM, disco y dependencias; superficie de ataque mínima.
- Un panel web o webhook exigiría reintroducir HTTP como feature aparte (Fase 8).
- Ver `DOCS/ESPECIFICACION.md` (secciones 3, 5, 9.1 y 12).
