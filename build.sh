#!/usr/bin/env bash
# Script de build para Render
set -o errexit
 
echo "==> Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt
 
echo "==> Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "==> Eliminando archivos de testing (no necesarios en producción)..."
rm -rf apps/sigesi/tests/
rm -f pytest.ini .coverage
 
echo "==> Build completado!"