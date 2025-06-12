#!/usr/bin/env bash
set -euo pipefail

echo "⏳ Starting setup…"

# 1. Python (global) – upgrade pip & install top-level requirements
echo "🐍 Installing Python dependencies (root)…"
python3 -m pip install --upgrade pip
[[ -f requirements.txt ]] && pip install -r requirements.txt

# 2. Python (per-service) – loop through subfolders with requirements.txt
for svc in services/*; do
  if [[ -f "$svc/requirements.txt" ]]; then
    echo "🐍 Installing Python dependencies for $svc"
    pip install -r "$svc/requirements.txt"
  fi
done

# 3. Node.js (webapp or other JS services)
if [[ -d "webapp" ]]; then
  echo "🟢 Installing Node.js dependencies & building webapp…"
  cd webapp
  npm ci
  npm run build || true
  cd ..
fi

# 4. Database migrations (Alembic example)
if [[ -f "alembic.ini" ]]; then
  echo "🗄️  Applying database migrations via Alembic…"
  alembic upgrade head
fi

# 5. Any Make targets (if you have a Makefile)
if [[ -f Makefile ]]; then
  echo "🏗️  Running make all…"
  make all
fi

echo "✅ Setup complete!"