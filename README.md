# Nepal Property Monitor

🏠 **Production-grade property monitoring tool** that automatically tracks new rental listings on Nepal Property Bazaar and sends instant Discord notifications when properties matching your budget are found.

## Features

✅ **Automated Monitoring** - Continuously checks Nepal Property Bazaar every 15 minutes
✅ **Budget Filtering** - Only shows properties ≤ Rs 10,000/month (configurable)
✅ **Smart Detection** - Tracks property IDs + timestamps to identify truly new listings
✅ **Instant Notifications** - Rich Discord embeds with property details and priority indicators
✅ **Price Change Alerts** - Get notified when property prices drop
✅ **Production Ready** - SQLite storage, structured logging, graceful shutdown, systemd support
✅ **Senior-Level Code** - Type hints, dependency injection, comprehensive error handling

## Quick Start

### 1. Installation

```bash
# Clone or extract the project
cd nepal-property-monitor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Required Configuration:**
- `PROPMON_DISCORD_WEBHOOK_URL` - Your Discord webhook URL (already set in .env.example)

**Optional Configuration:**
- `PROPMON_MAX_PRICE` - Maximum price filter (default: 10000)
- `PROPMON_SCRAPE_INTERVAL_SECONDS` - Check interval (default: 900 = 15 minutes)
- `PROPMON_LOG_LEVEL` - Logging level (default: INFO)

### 3. Test Discord Webhook

```bash
# Test that your Discord webhook is working
python test_webhook.py
```

You should receive a test notification in your Discord channel! 🎉

### 4. Run the Monitor

```bash
# Run directly with Python
python -m property_monitor

# Or run in the background with systemd (see Production Deployment below)
```

## How It Works

### First Run (Initialization)
On the first run, the monitor:
1. Scrapes all current properties from Nepal Property Bazaar
2. Saves them to the database as a baseline
3. **Does NOT send notifications** (avoids spam)
4. Prints: `✅ Initialized with X properties. Monitoring started.`

### Subsequent Runs
Every 15 minutes (configurable), the monitor:
1. Scrapes current properties
2. Compares against database to find:
   - **New properties** (not seen before + posted < 24 hours + within budget)
   - **Price changes** (existing properties with different prices)
3. Sends Discord notifications for matches
4. Updates the database

### Priority Indicators

Discord notifications include priority levels based on price:

- 🔥 **URGENT - GREAT DEAL!** - Under Rs 7,000
- ⭐ **HIGH PRIORITY** - Rs 7,000 - 9,000
- ✓ **Within Budget** - Rs 9,000 - 10,000

## Project Structure

```
nepal-property-monitor/
├── src/property_monitor/
│   ├── __main__.py                 # Entry point with graceful shutdown
│   ├── config.py                   # Pydantic settings (type-safe config)
│   ├── logging_config.py           # Structured logging setup
│   ├── domain/
│   │   ├── models.py               # Pydantic data models
│   │   └── exceptions.py           # Custom exception hierarchy
│   ├── adapters/
│   │   ├── scrapers/
│   │   │   ├── base.py             # Scraper protocol
│   │   │   └── nepal_bazaar.py     # Nepal Bazaar scraper
│   │   ├── notifiers/
│   │   │   ├── base.py             # Notifier protocol
│   │   │   └── discord.py          # Discord webhook (rate-limited)
│   │   └── storage/
│   │       ├── base.py             # Storage protocol
│   │       └── sqlite_store.py     # SQLite storage (ACID)
│   └── services/
│       └── monitor_service.py      # Core business logic
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   └── unit/                       # Unit tests
├── scripts/systemd/                # Systemd service files
├── data/                           # Database & backups (auto-created)
├── .env                            # Configuration (not committed)
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Architecture

### Clean Architecture Principles

- **Dependency Injection**: All components are injected, making testing easy
- **Protocol-Based Interfaces**: Using Python Protocols instead of ABC
- **Single Responsibility**: Each module has one clear purpose
- **Type Safety**: Full type hints with mypy strict mode
- **Error Handling**: Custom exception hierarchy with detailed context

### Technology Choices

| Component | Library | Why |
|-----------|---------|-----|
| HTTP Client | `httpx` | Modern, async-ready, HTTP/2 support |
| HTML Parser | `selectolax` | 2-5x faster than BeautifulSoup |
| Configuration | `pydantic-settings` | Type-safe with validation |
| Logging | `structlog` | Structured logs (JSON in production) |
| Storage | SQLite | ACID guarantees, no extra setup |
| Retry Logic | `backoff` | Exponential backoff decorator |

## Configuration Reference

### Environment Variables

All configuration uses the `PROPMON_` prefix:

```bash
# Application
PROPMON_ENVIRONMENT=production        # production, development, staging
PROPMON_LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Scraping
PROPMON_SCRAPE_INTERVAL_SECONDS=900  # Check interval (900 = 15 min)
PROPMON_MAX_RETRIES=3                # HTTP retry attempts
PROPMON_REQUEST_TIMEOUT=30.0         # HTTP timeout (seconds)
PROPMON_MAX_PRICE=10000              # Maximum price filter (Rs)
PROPMON_TIME_WINDOW_HOURS=24         # Consider properties posted within X hours

# Storage
PROPMON_DATA_DIR=./data              # Data directory
PROPMON_BACKUP_ENABLED=true          # Enable automatic backups
PROPMON_BACKUP_RETENTION_DAYS=7      # Backup retention period

# Discord
PROPMON_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
PROPMON_DISCORD_RATE_LIMIT_PER_MINUTE=25  # Max 30 (Discord limit)

# URLs to Monitor
PROPMON_PROPERTY_URLS=["https://nepalpropertybazaar.com/search-results/?status%5B%5D=for-rent&location%5B%5D=&areas%5B%5D="]
```

## Production Deployment

### Systemd Service (Recommended)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/property-monitor.service
```

```ini
[Unit]
Description=Nepal Property Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/nepal-property-monitor
Environment="PATH=/home/YOUR_USERNAME/nepal-property-monitor/.venv/bin"
ExecStart=/home/YOUR_USERNAME/nepal-property-monitor/.venv/bin/python -m property_monitor

# Graceful shutdown
KillSignal=SIGINT
TimeoutStopSec=30

# Restart on failure
Restart=on-failure
RestartSec=10

# Resource limits
MemoryMax=512M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=property-monitor

[Install]
WantedBy=multi-user.target
```

**Enable and start the service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable property-monitor
sudo systemctl start property-monitor

# Check status
sudo systemctl status property-monitor

# View logs
sudo journalctl -u property-monitor -f
```

### Manual Background Run

```bash
# Run with nohup
nohup python -m property_monitor > monitor.log 2>&1 &

# Or use screen/tmux
screen -S property-monitor
python -m property_monitor
# Press Ctrl+A then D to detach
```

## Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run tests
pytest tests/

# With coverage
pytest --cov=src/property_monitor --cov-report=html tests/
```

### Manual Testing

```bash
# Test Discord webhook
python test_webhook.py

# Test scraper (fetch real data)
python test_scraper.py

# Test full system (dry run - won't send notifications)
python -m property_monitor  # Run once, then Ctrl+C
```

## Troubleshooting

### Issue: No properties found

**Solution**: Check if the website URL is correct and accessible:
```bash
curl -I "https://nepalpropertybazaar.com/search-results/?status%5B%5D=for-rent&location%5B%5D=&areas%5B%5D="
```

### Issue: Discord notifications not sending

**Solutions:**
1. Verify webhook URL is correct: `python test_webhook.py`
2. Check rate limiting: Monitor logs for "rate_limit_sleeping"
3. Ensure Discord channel has the webhook enabled

### Issue: Database locked errors

**Solution**: Only run one instance of the monitor at a time. Check for existing processes:
```bash
ps aux | grep property_monitor
# Kill if needed: kill <PID>
```

### Issue: Website structure changed

**Solution**: The scraper uses multiple fallback strategies, but if it completely fails:
1. Check logs for parsing errors
2. Run `python test_scraper.py` to see what's being extracted
3. Update selectors in `src/property_monitor/adapters/scrapers/nepal_bazaar.py`

## Monitoring & Maintenance

### View Logs

```bash
# Systemd logs
sudo journalctl -u property-monitor -f

# Or check log files (if configured)
tail -f property_monitor.log
```

### Database Management

```bash
# View database
sqlite3 data/properties.db

# Useful queries
SELECT COUNT(*) FROM properties;
SELECT * FROM properties ORDER BY first_seen_at DESC LIMIT 10;
SELECT * FROM properties WHERE price <= 10000 ORDER BY price ASC;

# Backup database manually
cp data/properties.db data/properties_backup_$(date +%Y%m%d).db
```

### Performance

- **Memory Usage**: ~50-100 MB
- **CPU Usage**: < 1% (spikes to ~10% during scraping)
- **Disk Usage**: ~1 MB per 1000 properties
- **Network**: ~400 KB per scraping cycle

## Safety & Ethics

This monitor is designed to be **respectful** to the website:

✅ 15-minute intervals (only 4 requests/hour)
✅ Randomized delays (14-16 min variance to avoid patterns)
✅ Realistic User-Agent headers
✅ Exponential backoff on errors
✅ Respect rate limits (max 3 retries)
✅ Graceful handling of errors (no hammering)

## License

This project is provided as-is for personal use in finding rental properties in Nepal.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review logs for detailed error messages
3. Verify configuration in `.env` file

---

**Built with ❤️ for property hunters in Nepal**
