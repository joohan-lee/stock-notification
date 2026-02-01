# Oracle Cloud Deployment Info

## Instance Details

| Item | Value |
|------|-------|
| Name | `instance-modo-20260129` |
| Shape | VM.Standard.E2.1.Micro (Always Free) |
| OS | Oracle Linux 9 |
| AD | AD-3 (US-ASHBURN) |
| Public IP | 157.151.233.33 (Ephemeral) |
| User | `opc` |

## SSH Access

```bash
ssh -i ~/.ssh/oracle-modo.key opc@157.151.233.33
```

## File Transfer

```bash
# Upload file to server
scp -i ~/.ssh/oracle-modo.key <local-file> opc@157.151.233.33:~/

# Download file from server
scp -i ~/.ssh/oracle-modo.key opc@157.151.233.33:<remote-file> ./

# Sync project (recommended)
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  -e "ssh -i ~/.ssh/oracle-modo.key" \
  ./ opc@157.151.233.33:~/stock-notification/
```

## SSH Key Location

```
~/.ssh/oracle-modo.key
```

---

## Server Setup

### Swap Configuration (Required)

The 1GB RAM instance needs swap for `uv` and Python operations:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make persistent across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify:

```bash
free -h
# Should show 2.0G swap
```

### Install uv and Python 3.13

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Install Python 3.13
uv python install 3.13

# Verify
uv --version
python3.13 --version
```

### Deploy Project

```bash
# From local machine
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  -e "ssh -i ~/.ssh/oracle-modo.key" \
  ./ opc@157.151.233.33:~/stock-notification/

# On server
cd ~/stock-notification
uv pip install --system .
```

### Configure

```bash
cp config.example.yaml config.yaml
nano config.yaml

nano .env
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Initialize

```bash
uv run modo symbols sync
uv run modo user add --discord "$DISCORD_WEBHOOK_URL"
uv run modo watchlist add --user 1 --symbols SPY,DIA,QQQM
uv run modo rules add --user 1 --type monthly_high_drop --params '{"thresholds": [-3, -5, -10, -15, -20]}'
```

---

## Cron Configuration

```bash
crontab -e
```

```cron
# Modo: Alert check every hour
0 * * * * cd ~/stock-notification && /home/opc/.local/bin/uv run modo check >> ~/stock-notification/logs/cron.log 2>&1

# Modo: Healthcheck every Sunday at 02:00 UTC
0 2 * * 0 cd ~/stock-notification && /home/opc/.local/bin/uv run modo healthcheck >> ~/stock-notification/logs/cron.log 2>&1
```

```bash
mkdir -p ~/stock-notification/logs
```

---

## Log Monitoring

```bash
# View recent logs
tail -50 ~/stock-notification/logs/cron.log

# Follow logs
tail -f ~/stock-notification/logs/cron.log

# Check cron execution history
sudo grep modo /var/log/cron
```

---

## Healthcheck

The weekly healthcheck cron job (Sunday 02:00 UTC) sends a Discord notification confirming the service is running. This helps detect if cron has stopped or the instance was restarted.

---

## Notes

- Ephemeral IP: changes if instance is stopped and restarted
- To get a permanent IP, switch to Reserved Public IP in the console
- Always Free tier: no charges as long as within limits
- Swap is required: `uv` operations fail on 1GB RAM without it
