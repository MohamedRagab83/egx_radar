# Deployment Guide — EGX Radar v0.8.3

> Production deployment, configuration, monitoring, and scaling guidelines

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Standard Deployment](#standard-deployment)
3. [Docker Deployment](#docker-deployment)
4. [System Configuration](#system-configuration)
5. [Monitoring & Logging](#monitoring--logging)
6. [Scaling](#scaling)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] No syntax errors (`flake8 egx_radar`)
- [ ] Code formatted properly (`black --check egx_radar`)
- [ ] Performance targets met (backtest < 20s)
- [ ] Data validation configured
- [ ] Error handling enabled
- [ ] Logging configured
- [ ] Security credentials stored in environment variables
- [ ] Database migrations complete (if applicable)
- [ ] Backup strategy defined

---

## Standard Deployment

### 1. Server Requirements

**Minimum Specifications:**

```
CPU:    2+ cores (4+ recommended)
RAM:    2 GB minimum (4+ GB recommended)
Disk:   50 GB SSD (for backtest results & logs)
OS:     Linux (Ubuntu 18.04+), macOS, Windows Server 2016+
Python: 3.8, 3.9, 3.10, or 3.11
```

**Recommended Production Setup:**

```
CPU:    4+ cores (8+ for high-volume)
RAM:    8 GB
Disk:   100 GB SSD
OS:     Ubuntu 20.04 LTS
Python: 3.11 (latest stable)
```

### 2. Installation Steps

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# 3. Create application user
sudo useradd -m -s /bin/bash egx-radar

# 4. Clone repository
sudo -u egx-radar git clone https://github.com/yourusername/egx-radar.git /home/egx-radar/app

# 5. Create virtual environment
sudo -u egx-radar python3.11 -m venv /home/egx-radar/app/.venv

# 6. Install dependencies
sudo -u egx-radar /home/egx-radar/app/.venv/bin/pip install -r /home/egx-radar/app/requirements.txt

# 7. Test installation
sudo -u egx-radar /home/egx-radar/app/.venv/bin/python -m egx_radar --version

# 8. Create logs directory
sudo mkdir -p /var/log/egx-radar
sudo chown egx-radar:egx-radar /var/log/egx-radar

# 9. Create data directory
sudo mkdir -p /var/data/egx-radar
sudo chown egx-radar:egx-radar /var/data/egx-radar
```

### 3. Configuration

Edit `/home/egx-radar/app/egx_radar/config/settings.py`:

```python
# Production settings
WORKERS_COUNT = 4              # Adjust based on CPU cores
MAX_BACKTEST_SECONDS = 60      # Timeout enforcement
PERFORMANCE_PROFILE = "optimized"

# Enable logging
ENABLE_LOGGING = True
LOG_FILE = "/var/log/egx-radar/app.log"
LOG_LEVEL = "INFO"

# Data paths
DATA_DIR = "/var/data/egx-radar"
RESULTS_DIR = "/var/data/egx-radar/results"

# Error handling
ENABLE_ERROR_RECOVERY = True
RECOVERY_LOG = "/var/log/egx-radar/errors.json"
```

### 4. Systemd Service

Create `/etc/systemd/system/egx-radar.service`:

```ini
[Unit]
Description=EGX Radar Trading Engine
After=network.target

[Service]
Type=simple
User=egx-radar
WorkingDirectory=/home/egx-radar/app
Environment="PATH=/home/egx-radar/app/.venv/bin"
ExecStart=/home/egx-radar/app/.venv/bin/python -m egx_radar
Restart=always
RestartSec=10
StandardOutput=append:/var/log/egx-radar/service.log
StandardError=append:/var/log/egx-radar/service.err

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable egx-radar
sudo systemctl start egx-radar
sudo systemctl status egx-radar
```

---

## Docker Deployment

### Building Docker Image

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from egx_radar.backtest.engine import run_backtest; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "egx_radar"]
```

### Building and Running

```bash
# Build image
docker build -t egx-radar:latest .

# Run container
docker run -d \
  --name egx-radar-prod \
  --restart always \
  -e LOG_FILE=/app/logs/app.log \
  -v ./logs:/app/logs \
  -v ./data:/app/data \
  egx-radar:latest

# Check logs
docker logs -f egx-radar-prod

# Stop container
docker stop egx-radar-prod
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  egx-radar:
    build: .
    container_name: egx-radar-prod
    restart: always
    environment:
      - WORKERS_COUNT=4
      - MAX_BACKTEST_SECONDS=60
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import egx_radar"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  # Optional: Monitoring with Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
```

Run:

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## System Configuration

### Environment Variables

Essential variables for production:

```bash
# Performance
export EGX_RADAR_WORKERS=4
export EGX_RADAR_TIMEOUT=60

# Logging
export EGX_RADAR_LOG_FILE=/var/log/egx-radar/app.log
export EGX_RADAR_LOG_LEVEL=INFO

# Data
export EGX_RADAR_DATA_DIR=/var/data/egx-radar
export EGX_RADAR_RESULTS_DIR=/var/data/egx-radar/results

# Error Handling
export EGX_RADAR_ERROR_RECOVERY=true
export EGX_RADAR_ERROR_LOG=/var/log/egx-radar/errors.json

# Security
export EGX_RADAR_API_KEY=${SECRET_API_KEY}
export EGX_RADAR_DB_PASSWORD=${SECRET_DB_PASSWORD}
```

### File Permissions

Ensure correct permissions:

```bash
# Application files (read-only for app user)
sudo chmod -R 550 /home/egx-radar/app

# Config files
sudo chmod 440 /home/egx-radar/app/egx_radar/config/settings.py

# Log directory (writable)
sudo chmod 770 /var/log/egx-radar
sudo chown egx-radar:egx-radar /var/log/egx-radar

# Data directory (writable)
sudo chmod 770 /var/data/egx-radar
sudo chown egx-radar:egx-radar /var/data/egx-radar
```

### Resource Limits

Set limits in `/etc/security/limits.conf`:

```
egx-radar soft nofile 65536
egx-radar hard nofile 65536
egx-radar soft nproc 4096
egx-radar hard nproc 4096
```

---

## Monitoring & Logging

### Application Logs

Configure logging in `settings.py`:

```python
ENABLE_LOGGING = True
LOG_FILE = "/var/log/egx-radar/app.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Log Rotation

Create `/etc/logrotate.d/egx-radar`:

```
/var/log/egx-radar/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 egx-radar egx-radar
    sharedscripts
    postrotate
        systemctl reload egx-radar > /dev/null 2>&1 || true
    endscript
}
```

Activate:

```bash
sudo systemctl restart rsyslog
```

### Monitoring Health

Script to monitor service health (`/usr/local/bin/check-egx-radar.sh`):

```bash
#!/bin/bash

# Check if service is running
systemctl is-active --quiet egx-radar
if [ $? -ne 0 ]; then
    echo "ERROR: egx-radar service is not running"
    systemctl start egx-radar
    exit 1
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# Check log file size
LOG_SIZE=$(du -sh /var/log/egx-radar | awk '{print $1}')
echo "Log directory size: $LOG_SIZE"

echo "Status: OK"
exit 0
```

Make executable and add to crontab:

```bash
sudo chmod +x /usr/local/bin/check-egx-radar.sh
sudo crontab -e

# Add: */10 * * * * /usr/local/bin/check-egx-radar.sh > /dev/null 2>&1
```

---

## Scaling

### Horizontal Scaling

Run multiple instances with load balancer:

```bash
# Instance 1
sudo systemctl start egx-radar@1

# Instance 2
sudo systemctl start egx-radar@2

# Instance 3
sudo systemctl start egx-radar@3
```

Use Nginx as reverse proxy:

```nginx
upstream egx_radar {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name egx-radar.example.com;
    
    location / {
        proxy_pass http://egx_radar;
        proxy_set_header Host $host;
    }
}
```

### Vertical Scaling

Adjust for larger instances:

```python
# For 8-core CPU:
WORKERS_COUNT = 8

# For 16 GB RAM:
CHUNK_SIZE = 4
MAX_BACKTEST_SECONDS = 120

# For high-volume:
PERFORMANCE_PROFILE = "aggressive"
```

---

## Security

### Access Control

Restrict application access:

```bash
# Only allow local access
sudo ufw allow from 127.0.0.1 to any port 8000

# Or specific IP ranges (trading desk)
sudo ufw allow from 10.0.0.0/8 to any port 8000
```

### Secrets Management

Use environment variables for secrets:

```bash
# Never hardcode credentials
export DB_PASSWORD=<secret-password>
export API_KEY=<secret-key>

# In code:
import os
DB_PASSWORD = os.getenv('DB_PASSWORD')
API_KEY = os.getenv('API_KEY')
```

### SSL/TLS

If exposing UI:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    location / {
        proxy_pass http://egx_radar;
    }
}
```

### File Integrity

Monitor file changes:

```bash
# Install aide
sudo apt install aide aide-common -y

# Initialize database
sudo aideinit

# Check for changes
sudo aide --check
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status egx-radar

# View service logs
sudo journalctl -u egx-radar -n 50

# Manual test
sudo -u egx-radar /home/egx-radar/app/.venv/bin/python -m egx_radar --version
```

### High Memory Usage

```bash
# Check memory consumption
ps aux | grep egx-radar

# Reduce workers
export WORKERS_COUNT=2

# Reduce batch size
export CHUNK_SIZE=1
```

### Slow Performance

```bash
# Check system load
uptime

# Check disk I/O
iostat -x 1 5

# Check network (if fetching data)
iftop
```

### Logging Issues

```bash
# Check log file permissions
ls -la /var/log/egx-radar/

# Check disk space
df -h

# Rotate logs manually
sudo logrotate -f /etc/logrotate.d/egx-radar
```

---

## Backup & Recovery

### Automated Backups

Create backup script (`/usr/local/bin/backup-egx-radar.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/backups/egx-radar"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_DIR/data_$DATE.tar.gz /var/data/egx-radar/

# Backup config
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /home/egx-radar/app/egx_radar/config/

# Keep only last 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Schedule daily:

```bash
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-egx-radar.sh
```

### Restore from Backup

```bash
# Stop service
sudo systemctl stop egx-radar

# Restore data
sudo tar -xzf /backups/egx-radar/data_20260316_020000.tar.gz -C /

# Restore config
sudo tar -xzf /backups/egx-radar/config_20260316_020000.tar.gz -C /

# Fix permissions
sudo chown -R egx-radar:egx-radar /var/data/egx-radar
sudo chown -R egx-radar:egx-radar /home/egx-radar/app

# Restart service
sudo systemctl start egx-radar
```

---

## Performance Tuning

### CPU Optimization

```bash
# Check CPU cores
nproc

# Set workers = CPU cores - 1
export WORKERS_COUNT=3  # For 4-core CPU
```

### Memory Optimization

```python
# Reduce batch size for restricted RAM
CHUNK_SIZE = 1

# Limit backtest date range
MAX_BACKTEST_YEARS = 5
```

### Disk Optimization

```bash
# Use SSD for data directory
# Use tmpfs for temporary files
sudo mount -t tmpfs -o size=2G tmpfs /tmp

# Enable compression for logs
gzip -9 /var/log/egx-radar/*.log
```

---

## Maintenance

### Regular Checks

```bash
# Weekly: Run test suite
sudo -u egx-radar /home/egx-radar/app/.venv/bin/pytest tests/ -q

# Monthly: Update dependencies
sudo -u egx-radar /home/egx-radar/app/.venv/bin/pip list --outdated
sudo -u egx-radar /home/egx-radar/app/.venv/bin/pip install --upgrade <package>

# Quarterly: Deep security review
sudo apt audit
```

### Update Process

```bash
# 1. Backup current version
sudo cp -r /home/egx-radar/app /home/egx-radar/app.backup

# 2. Stop service
sudo systemctl stop egx-radar

# 3. Pull latest code
sudo -u egx-radar git -C /home/egx-radar/app pull origin main

# 4. Install updated dependencies
sudo -u egx-radar /home/egx-radar/app/.venv/bin/pip install -r /home/egx-radar/app/requirements.txt

# 5. Run tests
sudo -u egx-radar /home/egx-radar/app/.venv/bin/pytest /home/egx-radar/app/tests/ -q

# 6. Restart service
sudo systemctl start egx-radar

# 7. Monitor for errors
sudo journalctl -u egx-radar -f
```

---

**Last Updated:** March 16, 2026  
**Version:** EGX Radar 0.8.3  
[Back to README](README.md)
