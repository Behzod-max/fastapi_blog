#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-master}"
SERVICE_NAME="${SERVICE_NAME:-fastapi_blog.service}"
VENV_DIR="${VENV_DIR:-venv}"

cd "$APP_DIR"
git pull --ff-only origin "$DEPLOY_BRANCH"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements-production.txt
"$VENV_DIR/bin/alembic" upgrade head
sudo -n systemctl restart "$SERVICE_NAME"

echo "Deploy completed successfully."
