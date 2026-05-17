# 🚀 Production Deployment Guide

## Pre-Deployment Checklist

- [ ] All files committed to git
- [ ] `.gitignore` excludes data files and secrets
- [ ] `config.py` has optimal parameters
- [ ] `requirements.txt` is up to date
- [ ] README.md is complete
- [ ] Backtest results verified

## Step 1: Initialize Git Repository

```bash
cd /Users/kpal/projects/hermese

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Log-Fib Geometric Scalper v1.0

- Optimal configuration: 95.25% win rate, 2.56 profit factor
- 653 trades backtested on 20,639 bars XAGUSD 1min data
- Zero lagging indicators (pure geometric strategy)
- Production-ready scalper with live signals"

# Create main branch
git branch -M main
```

## Step 2: Create GitHub Repository

```bash
# Go to GitHub.com and create a new repository:
# Name: log-fib-scalper
# Description: "Geometric Scalping Strategy - 95% Win Rate"
# Visibility: Private (recommended for trading strategies)
# DO NOT initialize with README (we already have one)
```

## Step 3: Push to GitHub

```bash
# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/log-fib-scalper.git

# Push
git push -u origin main
```

## Step 4: Deploy to Production Server

### Option A: VPS Deployment (Recommended)

```bash
# SSH into your VPS
ssh user@your-server.com

# Clone repository
git clone https://github.com/YOUR_USERNAME/log-fib-scalper.git
cd log-fib-scalper

# Install Python (if needed)
sudo apt-get install python3 python3-pip

# Install dependencies
pip3 install -r requirements.txt

# Add your data file
scp data/OANDA_XAGUSD1.csv user@your-server.com:~/log-fib-scalper/data/

# Run the scalper
python3 scripts/log_fib_scalper_production.py
```

### Option B: Docker Deployment

```bash
# Create Dockerfile (see docker/ directory)
docker build -t log-fib-scalper .

# Run container
docker run -v $(pwd)/data:/app/data log-fib-scalper
```

### Option C: Cloud Deployment (AWS/GCP/Azure)

```bash
# Create VM instance
# Install git, python3
# Clone repository
# Set up cron job for continuous monitoring
```

## Step 5: Set Up Continuous Monitoring

### Create a systemd service (Linux VPS)

```bash
# Create service file
sudo nano /etc/systemd/system/log-fib-scalper.service

# Add this content:
[Unit]
Description=Log-Fib Geometric Scalper
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/log-fib-scalper
ExecStart=/usr/bin/python3 /home/your-user/log-fib-scalper/scripts/log_fib_scalper_production.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable log-fib-scalper
sudo systemctl start log-fib-scalper

# Check status
sudo systemctl status log-fib-scalper
```

## Step 6: Set Up Alerts (Optional)

### Email Alerts on Signals

```python
# Add to scripts/log_fib_scalper_production.py
import smtplib
from email.mime.text import MIMEText

def send_alert(signal):
    msg = MIMEText(f"New Signal: {signal}")
    msg['Subject'] = 'Log-Fib Scalper Alert'
    msg['From'] = 'your-email@gmail.com'
    msg['To'] = 'your-phone@vtext.com'  # SMS gateway
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('your-email', 'your-password')
    server.send_message(msg)
    server.quit()
```

## Step 7: Monitor Performance

```bash
# View logs
tail -f logs/scalper.log

# Check systemd service
journalctl -u log-fib-scalper -f

# Monitor git for updates
git pull origin main
```

## Security Best Practices

1. **Never commit API keys** — Use environment variables
2. **Keep repository private** — Trading strategies are valuable IP
3. **Use SSH keys** — For git authentication, not passwords
4. **Enable 2FA** — On GitHub and all deployment platforms
5. **Regular backups** — Of both code and data

## Troubleshooting

### Issue: Git push fails with authentication error
```bash
# Use personal access token instead of password
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/log-fib-scalper.git
```

### Issue: Python module not found
```bash
# Ensure you're in the project directory
cd /path/to/log-fib-scalper
python3 -m pip install -r requirements.txt
```

### Issue: Data file not found
```bash
# Verify data file exists
ls -la data/

# Check file permissions
chmod 644 data/OANDA_XAGUSD1.csv
```

---

*Deployment guide created by Hermes Quant Squad*
