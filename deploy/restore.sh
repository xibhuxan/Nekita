#!/usr/bin/env bash
# Restaura una copia de seguridad de Nekita (spec 7.7).
#
#   sudo deploy/restore.sh /var/lib/nekita/backups/nekita_2026-10-27T04-00-00.db
#
# Pasos: comprobar la copia -> parar el servicio -> apartar la BD actual ->
# copiar la copia -> borrar -wal/-shm -> arrancar.
# Variables: NEKITA_DATA_DIR (por defecto /var/lib/nekita), NEKITA_SERVICE (por
# defecto nekita; "none" para no tocar systemd, util en pruebas).
set -euo pipefail

COPIA="${1:-}"
DATA_DIR="${NEKITA_DATA_DIR:-/var/lib/nekita}"
SERVICE="${NEKITA_SERVICE:-nekita}"
PY="${NEKITA_PYTHON:-python3}"

if [[ -z "$COPIA" || ! -f "$COPIA" ]]; then
  echo "Uso: $0 <fichero-de-copia.db>" >&2
  exit 2
fi

echo "Comprobando la copia: $COPIA"
RESULTADO="$("$PY" - "$COPIA" <<'EOF'
import sqlite3, sys
try:
    con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
    print(con.execute("PRAGMA integrity_check").fetchone()[0])
except sqlite3.Error as exc:
    print(f"no es una base de datos valida ({exc})")
EOF
)"
if [[ "$RESULTADO" != "ok" ]]; then
  echo "La copia esta danada (integrity_check: $RESULTADO). No se restaura nada." >&2
  exit 1
fi

[[ "$SERVICE" != "none" ]] && systemctl stop "$SERVICE"

DESTINO="$DATA_DIR/nekita.db"
mkdir -p "$DATA_DIR"
if [[ -f "$DESTINO" ]]; then
  APARTADA="$DESTINO.antes-de-restaurar.$(date +%Y%m%dT%H%M%S)"
  mv "$DESTINO" "$APARTADA"
  echo "BD anterior guardada en: $APARTADA"
fi
rm -f "$DESTINO-wal" "$DESTINO-shm"
cp "$COPIA" "$DESTINO"
chmod 600 "$DESTINO"
if [[ "$SERVICE" != "none" ]] && id nekita >/dev/null 2>&1; then
  chown nekita:nekita "$DESTINO"
fi

[[ "$SERVICE" != "none" ]] && systemctl start "$SERVICE"
echo "Restauracion completada."
