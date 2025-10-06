#!/bin/bash
# Script para reconstruir completamente los contenedores Docker

echo "======================================================================"
echo "Reconstruyendo contenedores Docker de BandangWeb API"
echo "======================================================================"
echo ""

# Detener y eliminar contenedores, redes y volúmenes
echo "1. Deteniendo y eliminando contenedores, redes y volúmenes..."
docker-compose -f docker/docker-compose.yml down -v

echo ""
echo "2. Reconstruyendo imágenes sin caché..."
docker-compose -f docker/docker-compose.yml build --no-cache

echo ""
echo "3. Iniciando contenedores..."
docker-compose -f docker/docker-compose.yml up -d

echo ""
echo "======================================================================"
echo "✓ Reconstrucción completada"
echo "======================================================================"
echo ""
echo "Para ver los logs, ejecuta:"
echo "  docker-compose -f docker/docker-compose.yml logs -f app"
