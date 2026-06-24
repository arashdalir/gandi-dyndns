# Gandi Dynamic DNS Updater

A self-contained Python script to automatically update Gandi DNS A/AAAA records with your home server's current public IP address.

**Project Structure:**
- Script and dependencies stay in the application directory (no files copied to `/etc/` or `/opt/`)
- Config file location is flexible:
  - Default: `config.json` in the script directory
  - Or: Custom path (e.g., `/etc/dyndns/config.json`) specified during installation
- Systemd files are generated dynamically with the correct paths
- Easy to move or backup the script directory
- Single script can manage multiple domains with different config files

## Installation

### Quick Start: Systemd Service (Recommended)

Everything stays in the current directory. The installer generates systemd files with the correct paths automatically.

#### 1. Install Dependencies

```bash
pip install requests
```

#### 2. Configure

**Option A: Config in the app directory (recommended for single-server setups)**

```bash
cp config.example.json config.json
nano config.json
```

**Option B: Config in a custom location (for shared/multi-server setups)**

```bash
mkdir -p /etc/dyndns
cp config.example.json /etc/dyndns/my-domain.json
nano /etc/dyndns/my-domain.json
```

Fill in your details:
- `domain`: Your domain (e.g., `example.com`)
- `api_key`: Your Gandi Personal Access Token (from Gandi Admin → Organization)
- `ttl`: Time to live in seconds (default: 3600)
- `records`: List of subdomains to update with their types (A or AAAA)

#### 3. Test the Script

**If config is in the app directory:**
```bash
python3 update_dns.py
```

**If config is in a custom location:**
```bash
python3 update_dns.py /etc/dyndns/my-domain.json
```

You should see output confirming the updates (or config errors if needed).

#### 4. Install the Systemd Service

**If config is in the app directory:**
```bash
sudo python3 install.py
```

**If config is in a custom location:**
```bash
sudo python3 install.py --config /etc/dyndns/my-domain.json
```

The installer will:
- Generate systemd service and timer files with correct paths
- Embed the config file path in the service file
- Install to `/etc/systemd/system/`
- Enable and start the timer

#### 5. Verify

Check the timer is running:
```bash
systemctl status gandi-dyndns.timer
```

View logs:
```bash
journalctl -u gandi-dyndns.service -f
```

Manually trigger an update:
```bash
systemctl start gandi-dyndns.service
```

#### 6. Uninstall (if needed)

```bash
sudo systemctl stop gandi-dyndns.timer
sudo systemctl disable gandi-dyndns.timer
sudo rm /etc/systemd/system/gandi-dyndns.*
sudo systemctl daemon-reload
```

---

## Manual Setup: Cron (Alternative)

If you prefer cron instead of systemd:

### 1. Install Dependencies

```bash
pip install requests
```

### 2. Create Config

```bash
cp config.example.json config.json
nano config.json
```

### 3. Test

```bash
python3 update_dns.py
```

You should see output confirming the updates:
```
2026-06-24 12:34:56,123 - INFO - Starting DNS update for domain: example.com (2 records)
2026-06-24 12:34:58,456 - INFO - ✓ Updated home.example.com (A): 203.0.113.42
2026-06-24 12:34:59,789 - INFO - ✓ Updated vpn.example.com (A): 203.0.113.42
2026-06-24 12:35:00,012 - INFO - Update complete: 2 successful, 0 failed
```

### 4. Add to Crontab

Edit your crontab:
```bash
crontab -e
```

**If config is in the app directory:**
```
*/5 * * * * cd /path/to/dyndns && /usr/bin/python3 update_dns.py
```

**If config is in a custom location:**
```
*/5 * * * * /usr/bin/python3 /path/to/dyndns/update_dns.py /etc/dyndns/my-domain.json
```

Or run every hour instead of every 5 minutes:
```
0 * * * * /usr/bin/python3 /path/to/dyndns/update_dns.py /path/to/config.json
```

### Logging with Cron

If you want to log to a file:
```bash
*/5 * * * * /usr/bin/python3 /path/to/dyndns/update_dns.py /path/to/config.json >> /var/log/dyndns.log 2>&1
```

## Features

- ✅ Automatic public IP detection (IPv4 and IPv6)
- ✅ Updates multiple subdomains within a domain
- ✅ Flexible config file location (app directory or custom path)
- ✅ Single script manages multiple domains (with different config files)
- ✅ Logs to stdout and systemd journal
- ✅ Continues on errors (updates remaining records even if one fails)
- ✅ Returns proper exit codes (0 = success, 1 = any failures)

## Multi-Domain Example

If you have multiple domains, you can use the same script with different config files:

```bash
# Install for domain1.com
sudo python3 install.py --config /etc/dyndns/domain1.json

# Install for domain2.com (in a separate systemd service)
# Note: You'd need to clone the script or use the same one with different configs
sudo python3 install.py --config /etc/dyndns/domain2.json
```

Then set up cron jobs to run both:
```bash
*/5 * * * * /usr/bin/python3 /path/to/dyndns/update_dns.py /etc/dyndns/domain1.json
*/5 * * * * /usr/bin/python3 /path/to/dyndns/update_dns.py /etc/dyndns/domain2.json
```

## Troubleshooting

### General

**"Config file not found"**
- Make sure you specify the full path to your config file
- For systemd: config should be at `/etc/gandi-dyndns/config.json`

**"Invalid JSON in config file"**
- Verify your JSON syntax using a JSON validator

**"Failed to detect public IP"**
- Your home server may not have internet access
- The IP detection service (ifconfig.me) might be temporarily down
- The script continues with other operations

**"Network error" or "HTTP 401"**
- Check that your API key is correct and valid
- Verify your domain name is correct
- Check Gandi API status

### Systemd Service

**Timer not running**
```bash
systemctl status gandi-dyndns.timer
sudo systemctl start gandi-dyndns.timer
```

**View service logs**
```bash
journalctl -u gandi-dyndns.service -f
```

**View timer logs**
```bash
journalctl -u gandi-dyndns.timer -f
```

**Check when service last ran**
```bash
systemctl list-timers gandi-dyndns.timer
```

**Manually test the service**
```bash
systemctl start gandi-dyndns.service
sleep 1
journalctl -u gandi-dyndns.service --no-pager
```

**Reinstall service**
```bash
sudo systemctl stop gandi-dyndns.timer
sudo systemctl disable gandi-dyndns.timer
sudo python3 install.py
```

**Check service file paths**
The service file uses absolute paths to your current directory. If you move the directory, reinstall:
```bash
sudo python3 install.py
```
