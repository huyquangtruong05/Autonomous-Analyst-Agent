#!/usr/bin/env bash

set -e

echo "Starting Autonomous Analyst System..."

# Check Docker installed
if ! command -v docker &> /dev/null
then

echo "Docker is not installed!"

echo "Please install Docker Desktop first"
exit 1
fi

# Check Docker daemon running
if ! docker info &> /dev/null
then

echo "Docker is not running!"

echo "Please open Docker Desktop first"
exit 1

fi

# Check docker-compose 
if ! command -v docker-compose &> /dev/null
then

echo "docker-compose not found, try docker compose..."

COMPOSE_CMD="docker compose"
else

COMPOSE_CMD="docker-compose"
fi
# Check .env
if [ ! -f .env ]; then 
echo " .env file not found" 
echo " Please create .env file before running" 
exit 1
fi

# Stop old containers
echo "Cleaning old containers..."
$COMPOSE_CMD down

# Build & run 
echo " Building & starting containers..."
$COMPOSE_CMD up --build -d

#  Wait a bit
echo "Waiting for services to start..."
sleep 5

# Show status
echo " Running containers:"
docker ps

# Show URLs
echo ""
echo "Services:"
echo " FastAPI Docs: http://localhost:8000/docs"
echo " Neo4j Browser: http://localhost:7474"
echo ""

# Show logs
echo " Streaming logs (Ctrl+C to stop)..."
$COMPOSE_CMD logs -f