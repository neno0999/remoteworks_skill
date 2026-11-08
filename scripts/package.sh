#!/bin/sh
# Builds dist/remoteworks-matcher.zip for upload to claude.ai (folder at the zip root).
set -e
cd "$(dirname "$0")/.."
rm -rf dist && mkdir -p dist
python3 - <<'PY'
import os, zipfile
src = "skills/remoteworks-matcher"
with zipfile.ZipFile("dist/remoteworks-matcher.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(src):
        for f in files:
            if f.endswith(".pyc") or "__pycache__" in root:
                continue
            path = os.path.join(root, f)
            z.write(path, os.path.relpath(path, "skills"))
PY
echo "built dist/remoteworks-matcher.zip"
