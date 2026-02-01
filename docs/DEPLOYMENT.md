# Deployment Guide

## Overview

This guide covers deploying Modo on an Oracle Cloud Always Free tier instance using `uv` and system cron.

---

## Prerequisites

- Oracle Cloud account (Always Free tier)
- SSH key pair for instance access
- Discord webhook URL (for notifications)
- Local machine with `rsync` or `scp`

---

## Part 1: Oracle Cloud Instance Setup

See [Oracle Cloud](ORACLE_CLOUD.md) for detailed instance creation and configuration steps.

Summary of server preparation:

1. Create VM.Standard.E2.1.Micro instance (Oracle Linux 9)
2. Configure swap (2GB, required for 1GB RAM instances)
3. Install uv and Python 3.13
4. SSH access configured

---

## Part 2: Transfer Project to Server

### Option A: rsync (Recommended)

```bash
# From local machine - sync project files
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  -e "ssh -i ~/.ssh/oracle-modo.key" \
  ./ opc@157.151.233.33:~/stock-notification/
```

### Option B: scp

```bash
# Archive and transfer
tar czf modo.tar.gz --exclude='.venv' --exclude='__pycache__' --exclude='.git' .
scp -i ~/.ssh/oracle-modo.key modo.tar.gz opc@157.151.233.33:~/

# On server: extract
ssh -i ~/.ssh/oracle-modo.key opc@157.151.233.33
tar xzf modo.tar.gz -C ~/stock-notification
```

---

## Part 3: Server Configuration

### 3.1 Install Dependencies

```bash
cd ~/stock-notification
uv pip install --system .
```

### 3.2 Configure Application

```bash
# Copy example config
cp config.example.yaml config.yaml
nano config.yaml  # Edit as needed
```

### 3.3 Set Up Environment Variables

```bash
nano .env
# Add:
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 3.4 Initialize Database

```bash
uv run modo symbols sync
uv run modo user add --discord "$DISCORD_WEBHOOK_URL"
uv run modo watchlist add --user 1 --symbols SPY,DIA,QQQM
uv run modo rules add --user 1 --type monthly_high_drop --params '{"thresholds": [-3, -5, -10, -15, -20]}'
```

### 3.5 Test Run

```bash
uv run modo check --debug
```

---

## Part 4: Cron Job Setup

### 4.1 Edit Crontab

```bash
crontab -e
```

Add the following entries:

```cron
# Modo: Alert check every hour
0 * * * * cd ~/stock-notification && /home/opc/.local/bin/uv run modo check >> ~/stock-notification/logs/cron.log 2>&1

# Modo: Healthcheck every Sunday at 02:00 UTC
0 2 * * 0 cd ~/stock-notification && /home/opc/.local/bin/uv run modo healthcheck >> ~/stock-notification/logs/cron.log 2>&1
```

### 4.2 Create Log Directory

```bash
mkdir -p ~/stock-notification/logs
```

### 4.3 Verify Cron

```bash
# List active cron jobs
crontab -l

# Check cron service is running
systemctl status crond
```

---

## Part 5: Verification

### Check Logs

```bash
# View recent log output
tail -50 ~/stock-notification/logs/cron.log

# Follow logs in real-time
tail -f ~/stock-notification/logs/cron.log
```

### Manual Test

```bash
cd ~/stock-notification
uv run modo check
```

### Verify Cron Execution

```bash
# Check system cron log
sudo grep modo /var/log/cron
```

---

## Part 6: Updating

```bash
# From local machine - sync updated files
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  --exclude 'data' --exclude '.env' --exclude 'config.yaml' --exclude 'logs' \
  -e "ssh -i ~/.ssh/oracle-modo.key" \
  ./ opc@157.151.233.33:~/stock-notification/

# On server - reinstall if dependencies changed
ssh -i ~/.ssh/oracle-modo.key opc@157.151.233.33
cd ~/stock-notification
uv pip install --system .
```

---

## Part 7: Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No alerts received | Config error | Check `logs/cron.log` for errors |
| Discord webhook fails | Invalid URL | Verify webhook URL in `.env` |
| Rate limited by Yahoo | Too frequent requests | Increase check interval in cron |
| Cron not running | Service stopped | `sudo systemctl start crond` |
| Out of memory | 1GB RAM limit | Ensure swap is configured (see [Oracle Cloud](ORACLE_CLOUD.md)) |

### Debug Mode

```bash
cd ~/stock-notification
uv run modo check --debug
```

---

## Security Notes

1. **Never commit `.env` file** - Add to `.gitignore`
2. **Use environment variables** for all secrets
3. **Keep Oracle Cloud SSH key secure**
4. **Monitor usage** - Oracle may suspend for abuse
