#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=========================================="
echo "    INFRAMIND RENDER BUILD PIPELINE      "
echo "=========================================="

echo "[1/4] Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "[2/4] Installing backend Python production dependencies..."
cd backend
pip install -r requirements.txt

echo "[3/4] Pre-caching local embedding model weights..."
python -c "
from sentence_transformers import SentenceTransformer
print('Pre-downloading all-MiniLM-L6-v2 model weights for zero-latency startup...')
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print('Model loaded and cached successfully.')
"

echo "[4/4] Ensuring runtime directories exist..."
mkdir -p /var/data/uploads /var/data/chroma /var/data/processed /var/data/users || mkdir -p data/uploads data/chroma data/processed data/users

echo "=========================================="
echo "     INFRAMIND BUILD COMPLETE            "
echo "=========================================="
