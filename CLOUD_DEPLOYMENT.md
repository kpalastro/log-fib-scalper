# 🚀 Cloud Deployment Guide

**Deploy your Log-Fib Scalper to cloud for 24/7 live trading**

---

## 📋 Prerequisites

### 1. Cloud VPS Account (Choose One)

| Provider | Recommended Plan | Monthly Cost | Link |
|----------|-----------------|--------------|------|
| **DigitalOcean** | Basic Droplet (2GB RAM) | $12/mo | https://digitalocean.com |
| **AWS** | EC2 t3.small | $15/mo | https://aws.amazon.com |
| **Google Cloud** | e2-small | $10/mo | https://cloud.google.com |
| **Linode** | Nanode | $5/mo | https://linode.com |
| **Vultr** | Cloud Compute | $6/mo | https://vultr.com |

**Recommended:** DigitalOcean or Linode (simplest setup)

### 2. API Credentials

- **Gate.io API Keys:** https://www.gate.io/settings/api
- **IG Markets API Keys:** https://www.ig.com/uk/trading-api

---

## 🚀 Quick Deploy (Automated)

### Step 1: Create Cloud VPS

1.  Sign up for your chosen provider
2.  Create a new Ubuntu 22.04 LTS droplet/instance
3.  Note the public IP address
4.  SSH into your server:
    ```bash
    ssh root@YOUR_SERVER_IP
    ```

### Step 2: Run Deployment Script

```bash
# Clone the repository
cd /root
git clone https://github.com/kpalastro/log-fib-scalper.git
cd log-fib-scalper

# Run the automated deployment script
chmod +x deploy.sh
./deploy.sh
```

### Step 3: Configure Credentials

```bash
# Edit Gate.io credentials
nano live_trading/crypto/.env

# Edit IG Markets credentials
nano live_trading/.env
```

### Step 4: Restart Services

```bash
docker-compose restart
```

---

## 🐳 Manual Deploy (Docker)

### Step 1: Install Docker

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Clone Repository

```bash
cd /root
git clone https://github.com/kpalastro/log-fib-scalper.git
cd log-fib-scalper
```

### Step 3: Configure Environment

```bash
# Copy example files
cp live_trading/crypto/.env.example live_trading/crypto/.env
cp live_trading/.env.example live_trading/.env

# Edit with your credentials
nano live_trading/crypto/.env
nano live_trading/.env
```

### Step 4: Build & Run

```bash
# Build containers
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## 📊 Managing Services

### View Running Containers

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f crypto-btc
docker-compose logs -f forex-gold
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific
docker-compose restart crypto-btc
```

### Stop Services

```bash
docker-compose down
```

### Update to Latest Version

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### View Resource Usage

```bash
docker stats
```

---

## 🔒 Security Best Practices

### 1. Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 2. SSH Key Authentication

```bash
# Generate SSH key on your local machine
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy to server
ssh-copy-id root@YOUR_SERVER_IP

# Disable password authentication (on server)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Restart SSH: sudo systemctl restart sshd
```

### 3. Environment Variables

- **NEVER** commit `.env` files to git
- Store credentials securely
- Use strong API key permissions (read + trade only, no withdrawal)

### 4. Regular Updates

```bash
# Weekly system updates
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images monthly
docker-compose pull
docker-compose up -d
```

---

## 📈 Monitoring & Alerts

### 1. Check Service Status

```bash
# Check if containers are running
docker-compose ps

# Check container health
docker inspect --format='{{.State.Health.Status}}' log-fib-btc
```

### 2. Log Monitoring

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 crypto-btc

# Search logs
docker-compose logs crypto-btc | grep "TRADE OPENED"
```

### 3. Resource Monitoring

```bash
# CPU/Memory usage
docker stats

# Disk usage
df -h
docker system df
```

### 4. Set Up Alerts (Optional)

Create a monitoring script:

```bash
#!/bin/bash
# monitor.sh

# Check if containers are running
if ! docker-compose ps | grep -q "Up"; then
    # Send alert (email, Telegram, etc.)
    echo "⚠️  Trading container stopped!" | mail -s "Alert: Log-Fib Scalper" your-email@example.com
fi
```

Add to crontab:
```bash
crontab -e
# Add: */5 * * * * /root/log-fib-scalper/monitor.sh
```

---

## 💰 Cost Optimization

### Recommended VPS Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 1 GB | 2 GB |
| **CPU** | 1 vCPU | 2 vCPU |
| **Storage** | 20 GB SSD | 40 GB SSD |
| **Bandwidth** | 1 TB | 2 TB |

### Monthly Costs

| Provider | Plan | Cost |
|----------|------|------|
| DigitalOcean | Basic 2GB | $12/mo |
| Linode | Nanode | $5/mo |
| AWS | t3.small | $15/mo |
| **Total** | | **$5-15/mo** |

### Cost Saving Tips

1.  Use spot instances (AWS) - up to 70% off
2.  Commit to 1-year term - 30-40% off
3.  Use smaller VPS for testing, scale up for production
4.  Run only needed services (disable forex if only trading crypto)

---

## 🔧 Troubleshooting

### Issue: Container won't start

```bash
# Check logs
docker-compose logs crypto-btc

# Check environment variables
docker-compose exec crypto-btc env | grep GATE

# Restart container
docker-compose restart crypto-btc
```

### Issue: API connection failed

1.  Verify API credentials in `.env`
2.  Check API key permissions (must have trading enabled)
3.  Verify server can reach API endpoints:
    ```bash
    curl https://api.gateio.ws/api/v4/spot/accounts
    ```

### Issue: High memory usage

```bash
# Check memory usage
docker stats

# Restart container
docker-compose restart crypto-btc

# Reduce position size or trade frequency in config
```

### Issue: Disk space full

```bash
# Clean old Docker images
docker system prune -a

# Clear old logs
sudo truncate -s 0 logs/*.log

# Check disk usage
df -h
```

---

## 📞 Support

- **GitHub Issues:** https://github.com/kpalastro/log-fib-scalper/issues
- **Documentation:** https://github.com/kpalastro/log-fib-scalper/blob/main/README.md
- **Deployment Guide:** https://github.com/kpalastro/log-fib-scalper/blob/main/DEPLOYMENT.md

---

*Cloud Deployment Guide - Log-Fib Scalper v1.0*
