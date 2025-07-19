#!/bin/bash

echo "Checking system health..."

# Check if Docker is running
if ! systemctl is-active --quiet docker; then
    echo "ERROR: Docker is not running"
    exit 1
fi

# Check if containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "ERROR: Containers are not running"
    exit 1
fi

# Check API endpoint
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: API is not responding"
    exit 1
fi

echo "System is healthy"