#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# CLOUD DEPLOYMENT SCRIPT
# ═══════════════════════════════════════════════════════════════
# Automates deployment to cloud VPS (AWS, DigitalOcean, etc.)

set -e

echo "========================================"
echo "🚀 LOG-FIB SCALPER - CLOUD DEPLOYMENT"
echo "========================================"
echo

# Check if running on cloud VPS
if [ ! -f /etc/os-release ]; then
    echo "⚠️  Warning: This doesn't look like a Linux VPS"
    echo "   This script is designed for cloud Linux servers"
    echo "   (AWS EC2, DigitalOcean Droplet, Google Cloud, etc.)"
    echo
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🐙 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose already installed"
fi

# Add user to docker group
echo "🔧 Configuring Docker permissions..."
sudo usermod -aG docker $USER

# Clone repository (if not already cloned)
if [ ! -d "/home/$USER/log-fib-scalper" ]; then
    echo "📥 Cloning repository..."
    cd /home/$USER
    git clone https://github.com/kpalastro/log-fib-scalper.git
    cd log-fib-scalper
else
    echo "✅ Repository already exists"
    cd /home/$USER/log-fib-scalper
    git pull
fi

# Create logs directory
mkdir -p logs

# Copy environment files
echo "🔐 Setting up environment files..."
if [ ! -f "live_trading/crypto/.env" ]; then
    echo "⚠️  Creating crypto .env from template..."
    cp live_trading/crypto/.env.example live_trading/crypto/.env
    echo "   Please edit live_trading/crypto/.env with your Gate.io credentials"
fi

if [ ! -f "live_trading/.env" ]; then
    echo "⚠️  Creating forex .env from template..."
    cp live_trading/.env.example live_trading/.env
    echo "   Please edit live_trading/.env with your IG Markets credentials"
fi

# Build and start containers
echo "🚀 Building Docker containers..."
docker-compose build

echo "🎯 Starting trading agents..."
docker-compose up -d

# Show status
echo
echo "========================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================"
echo
echo "📊 Running Containers:"
docker-compose ps
echo
echo "📝 View Logs:"
echo "   docker-compose logs -f crypto-btc   # Bitcoin trading"
echo "   docker-compose logs -f forex-gold   # Gold trading"
echo
echo "🛑 Stop Services:"
echo "   docker-compose down"
echo
echo "🔄 Restart Services:"
echo "   docker-compose restart"
echo
echo "📈 Monitor Performance:"
echo "   docker stats"
echo
echo "========================================"
echo "⚠️  IMPORTANT: Edit .env files with your API credentials!"
echo "   - live_trading/crypto/.env (Gate.io)"
echo "   - live_trading/.env (IG Markets)"
echo "========================================"
