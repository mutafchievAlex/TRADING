#!/bin/bash

# PRODUCTION DEPLOYMENT GUIDE
# Trading System - XAUUSD Double Bottom Strategy
# Date: January 22, 2026

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Trading System - Deployment Guide${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Prerequisites Check
echo -e "${YELLOW}[STEP 1]${NC} Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "  Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "  Install from: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found: $(docker-compose --version)${NC}"

# Check disk space
DISK_SPACE=$(df . | awk 'NR==2 {print $4}')
if [ "$DISK_SPACE" -lt 1000000 ]; then
    echo -e "${RED}✗ Insufficient disk space (need 1GB)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Sufficient disk space: ${DISK_SPACE}KB${NC}"

echo ""

# Step 2: Configuration
echo -e "${YELLOW}[STEP 2]${NC} Verifying configuration..."

if [ ! -f "config/config.yaml" ]; then
    echo -e "${RED}✗ Config file not found: config/config.yaml${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Configuration file found${NC}"

# Check MT5 credentials in config
if grep -q "login:" config/config.yaml; then
    echo -e "${GREEN}✓ MT5 credentials configured${NC}"
else
    echo -e "${YELLOW}⚠ MT5 credentials may not be configured${NC}"
fi

echo ""

# Step 3: Directory Setup
echo -e "${YELLOW}[STEP 3]${NC} Setting up directories..."

mkdir -p data/backups
mkdir -p data/historical
mkdir -p logs
mkdir -p reports

echo -e "${GREEN}✓ Directories created${NC}"

echo ""

# Step 4: Build Docker Image
echo -e "${YELLOW}[STEP 4]${NC} Building Docker image (this may take 2-3 minutes)..."

if docker build -t trading_system:latest . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    echo "  Run manually: docker build -t trading_system:latest ."
    exit 1
fi

echo ""

# Step 5: Start Services
echo -e "${YELLOW}[STEP 5]${NC} Starting trading system..."

docker-compose up -d

echo -e "${GREEN}✓ Services started${NC}"

echo ""

# Step 6: Health Check
echo -e "${YELLOW}[STEP 6]${NC} Waiting for container to be ready..."

sleep 5

if docker-compose ps | grep -q "healthy"; then
    echo -e "${GREEN}✓ Container is healthy${NC}"
elif docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠ Container is starting (check logs in 30s)${NC}"
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo "  Check logs: docker-compose logs -f"
    exit 1
fi

echo ""

# Step 7: Verification
echo -e "${YELLOW}[STEP 7]${NC} Verifying deployment..."

# Check if container is running
CONTAINER_ID=$(docker-compose ps -q trading-bot 2>/dev/null)
if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}✗ Container is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Container running: $CONTAINER_ID${NC}"

# Check logs for errors
if docker logs $CONTAINER_ID | grep -q "ERROR"; then
    echo -e "${YELLOW}⚠ Errors found in logs (check below)${NC}"
else
    echo -e "${GREEN}✓ No errors in logs${NC}"
fi

echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ DEPLOYMENT SUCCESSFUL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo "Next steps:"
echo ""
echo "1. Monitor logs in real-time:"
echo -e "   ${YELLOW}docker-compose logs -f --tail=100${NC}"
echo ""
echo "2. Check container health every 5 minutes:"
echo -e "   ${YELLOW}docker-compose ps${NC}"
echo ""
echo "3. If something goes wrong:"
echo -e "   ${YELLOW}docker-compose logs | head -100  # See errors${NC}"
echo -e "   ${YELLOW}docker-compose down               # Stop all${NC}"
echo -e "   ${YELLOW}docker-compose up -d              # Restart${NC}"
echo ""
echo "4. To stop trading system:"
echo -e "   ${YELLOW}docker-compose down${NC}"
echo ""
echo "5. To update code:"
echo -e "   ${YELLOW}git pull${NC}"
echo -e "   ${YELLOW}docker build -t trading_system:latest .${NC}"
echo -e "   ${YELLOW}docker-compose restart${NC}"
echo ""
echo "Container Status:"
docker-compose ps
echo ""
echo "Recent logs:"
docker-compose logs --tail=5
echo ""
echo "Troubleshooting guide: See DOCKER_DEPLOYMENT.md"
echo ""
