#!/usr/bin/env bash
# Compiles assets/app.css -> static/css/app.css with the Tailwind CLI.
#
# The compiled file is committed, so running or deploying the app never needs
# Node. Run this after adding a utility class that no template used before, then
# commit the result (CI fails if static/css/app.css is out of date).
#
# Usage: scripts/build-css.sh [--watch]
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v npm > /dev/null; then
  echo "npm not found - install Node.js to rebuild the CSS." >&2
  exit 1
fi

# Versions are pinned in package.json; installed once into a gitignored node_modules.
[ -d node_modules/@tailwindcss/cli ] || npm install --silent --no-audit --no-fund

./node_modules/.bin/tailwindcss --input assets/app.css --output static/css/app.css --minify "$@"
