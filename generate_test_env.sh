#!/bin/bash

echo "🔍 Scanning project source for environment variables..."

# Directories to scan (edit if needed)
SCAN_DIRS="backend frontend src ."

# Exclude heavy/system folders
EXCLUDES="--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build --exclude-dir=.venv --exclude-dir=venv"

# Extract only project-level env vars
VARS=$(grep -RhoP $EXCLUDES \
"(?<=os\.getenv\(['\"])[A-Z0-9_]+|(?<=process\.env\.)[A-Z0-9_]+|(?<=import\.meta\.env\.)VITE_[A-Z0-9_]+" \
$SCAN_DIRS 2>/dev/null | sort -u)

if [ -z "$VARS" ]; then
  echo "⚠️ No project environment variables found."
  exit 1
fi

echo "🧪 Generating clean test.env..."

> test.env

for VAR in $VARS; do
  echo "$VAR=TEST_$VAR" >> test.env
done

echo "✅ test.env generated successfully."
echo ""
echo "📋 Project Variables Found:"
echo "$VARS"
echo ""

echo "🔎 Checking missing variables in current shell..."

MISSING=0

for VAR in $VARS; do
  if [ -z "${!VAR}" ]; then
    echo "❌ Missing: $VAR"
    MISSING=1
  fi
done

if [ $MISSING -eq 0 ]; then
  echo "✅ All required variables exist in shell."
else
  echo "⚠️ Some required variables are missing."
fi

echo ""
echo "🚀 Done."
