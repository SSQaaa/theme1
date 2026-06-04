#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_NAME="vits-melo-tts-zh_en"
ARCHIVE="${MODEL_NAME}.tar.bz2"
URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/${ARCHIVE}"

cd "$SCRIPT_DIR"

if [[ -f "${MODEL_NAME}/model.onnx" ]]; then
  echo "Model already exists: ${SCRIPT_DIR}/${MODEL_NAME}"
  exit 0
fi

echo "Downloading ${MODEL_NAME}..."
curl -fL "$URL" -o "$ARCHIVE"
tar xvf "$ARCHIVE"
rm "$ARCHIVE"
echo "Model ready: ${SCRIPT_DIR}/${MODEL_NAME}"
