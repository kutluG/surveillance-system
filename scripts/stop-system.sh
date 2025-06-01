#!/bin/bash
# System shutdown script

set -e

echo "🛑 Stopping Surveillance System"
echo "==============================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📦 Stopping all services...${NC}"
docker-compose down

echo -e "${GREEN}✅ All services stopped${NC}"

# Ask if user wants to remove volumes
read -p "Do you want to remove all data volumes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️  Removing volumes...${NC}"
    docker-compose down -v
    echo -e "${GREEN}✅ Volumes removed${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Surveillance System stopped successfully!${NC}"