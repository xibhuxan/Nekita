#!/usr/bin/env bash
# Instala Nekita en Debian con systemd (spec 12). Ejecutar como root desde el clone:
#
#   git clone https://github.com/Xibhu/Nekita && cd Nekita
#   sudo deploy/install.sh
#   sudo nano /etc/nekita/nekita.env     # poner NEKITA_TOKEN
#   sudo systemctl enable --now nekita
#
# Es idempotente: sirve tambien para actualizar (git pull && sudo deploy/install.sh).
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Ejecuta con sudo/root." >&2; exit 1; }

ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO=/opt/nekita
ENV_FILE=/etc/nekita/nekita.env
PYTHON="${PYTHON:-python3}"

"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)' || {
  echo "Hace falta Python >= 3.13 (encontrado: $("$PYTHON" --version 2>&1))." >&2
  echo "En Debian 13 (trixie): apt install python3 python3-venv. Otra ruta: PYTHON=/ruta/python3.13" >&2
  exit 1
}
"$PYTHON" -c 'import ensurepip, venv' 2>/dev/null || {
  echo "Falta python3-venv: apt install python3-venv" >&2
  exit 1
}
"$PYTHON" -c 'import sqlite3, sys; sys.exit(0 if sqlite3.sqlite_version_info >= (3, 37) else 1)' || {
  echo "SQLite demasiado antiguo: se necesita >= 3.37 (tablas STRICT)." >&2
  exit 1
}

echo "==> Usuario y carpetas"
id nekita >/dev/null 2>&1 || useradd --system --home-dir /var/lib/nekita --shell /usr/sbin/nologin nekita
install -d -o root -g root -m 755 "$DESTINO"
install -d -o root -g nekita -m 750 /etc/nekita

echo "==> Codigo en $DESTINO"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude '.git' --exclude '.venv' --exclude '.env' \
    --exclude '__pycache__' --exclude '.mypy_cache' --exclude '.ruff_cache' \
    --exclude '.pytest_cache' --exclude 'tests' "$ORIGEN"/ "$DESTINO"/
else
  find "$DESTINO" -mindepth 1 -maxdepth 1 ! -name .venv -exec rm -rf {} +
  tar -C "$ORIGEN" --exclude=.git --exclude=.venv --exclude=.env --exclude=tests \
    --exclude=__pycache__ --exclude=.mypy_cache --exclude=.ruff_cache \
    --exclude=.pytest_cache -cf - . | tar -C "$DESTINO" -xf -
fi

echo "==> Entorno virtual (versiones fijadas por uv.lock)"
[[ -d "$DESTINO/.venv" ]] || "$PYTHON" -m venv "$DESTINO/.venv"
"$DESTINO/.venv/bin/pip" install -q --disable-pip-version-check uv
(cd "$DESTINO" && UV_PROJECT_ENVIRONMENT="$DESTINO/.venv" "$DESTINO/.venv/bin/uv" sync --frozen --no-dev --no-progress)
"$DESTINO/.venv/bin/pip" uninstall -y -q uv   # no hace falta en ejecucion (~35 MB)

echo "==> Configuracion"
if [[ ! -f "$ENV_FILE" ]]; then
  install -m 640 -o root -g nekita "$ORIGEN/.env.example" "$ENV_FILE"
  echo "Creado $ENV_FILE: edita NEKITA_TOKEN antes de arrancar."
else
  echo "Se conserva $ENV_FILE"
fi

echo "==> systemd y journald"
install -m 644 "$ORIGEN/deploy/nekita.service" /etc/systemd/system/nekita.service
install -d /etc/systemd/journald.conf.d
install -m 644 "$ORIGEN/deploy/journald-nekita.conf" /etc/systemd/journald.conf.d/nekita.conf
systemctl daemon-reload
systemctl restart systemd-journald || true
if systemctl is-active --quiet nekita; then
  systemctl restart nekita
  echo "Servicio reiniciado."
fi

echo "==> Reloj (las poles dependen de la hora)"
if command -v timedatectl >/dev/null 2>&1; then
  timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes \
    && echo "Reloj sincronizado." \
    || echo "AVISO: reloj sin sincronizar. Activa NTP: timedatectl set-ntp true (o apt install systemd-timesyncd)."
fi

cat <<EOF

Listo. Siguientes pasos:
  1. sudoedit $ENV_FILE            (NEKITA_TOKEN y, si quieres, NEKITA_MASTER_ID)
  2. Para la version Node: parala antes (un token no admite dos instancias: error 409).
  3. sudo systemctl enable --now nekita
  4. journalctl -u nekita -f
Recomendado: sudo apt install unattended-upgrades   (parches de seguridad automaticos)
EOF
