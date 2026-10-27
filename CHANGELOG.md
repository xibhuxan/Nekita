# Changelog

## [Sin publicar] — 2.0.0 (reescritura en Python)
- Núcleo: aiogram 3 con polling, SQLite (WAL, migraciones, copias con `VACUUM INTO`),
  lock por chat, límites de uso, errores con referencia y parada limpia.
- Poles definidas por datos (`games.toml`): peninsular (4 puestos) y 7 poles de un puesto.
- Nekomandos con horas por zona, overrides en BD y /help automático.
- Imágenes: neko, perro, cangrejo y moneda con caché, plan B y tope de descarga.
- Admin: /stats, /grupos y anuncios globales o a grupos concretos con confirmación.
- Operación: servicio systemd con sandbox, `install.sh`, `restore.sh`, importador de Node.
- Presupuesto de RAM en reposo subido a 200 MB (ADR 0002).
