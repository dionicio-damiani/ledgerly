#!/bin/bash
set -e  # Salir si hay error

ORIGINAL_DATABASE_URL=$DATABASE_URL

# Transformar DATABASE_URL para Alembic (cambiar +asyncpg por +psycopg2)
export DATABASE_URL=$(echo "$ORIGINAL_DATABASE_URL" | sed 's/+asyncpg/+psycopg2/')
echo "Running migrations with: $DATABASE_URL"
alembic upgrade head

# Restaurar URL original (asyncpg) para la app
export DATABASE_URL=$ORIGINAL_DATABASE_URL

# Iniciar la app
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
