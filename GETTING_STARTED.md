# Getting Started with Nepal Property Monitor

## ✅ Installation Complete!

Your Nepal Property Monitor has been successfully built and tested. Here's what's ready:

### 🎯 What Was Built

1. **Production-Grade Architecture**
   - Type-safe configuration with Pydantic
   - Structured logging (JSON in production, colored in development)
   - SQLite database with ACID guarantees
   - Graceful shutdown handling
   - Comprehensive error handling

2. **Core Features**
   - Web scraper for Nepal Property Bazaar (with exponential backoff)
   - Discord notifier with rate limiting (30 req/min max)
   - Smart property detection (ID + timestamp validation)
   - Price change tracking
   - Automatic backups with 7-day retention

3. **Code Quality**
   - Full type hints (Python 3.10+)
   - Dependency injection for testability
   - Custom exception hierarchy
   - 15 passing unit tests
   - Comprehensive documentation

### ✅ Test Results

**Discord Webhook**: ✅ Working (test notification sent)
**Web Scraper**: ✅ Working (extracted 16 properties from live website)
**Database**: ✅ Working (properties saved to SQLite)
**Filtering**: ✅ Working (found 1 property ≤ Rs 10,000)
**Health Check**: ✅ Working (system healthy)
**Unit Tests**: ✅ 15/15 passed

## 🚀 Quick Start

### 1. Run the Monitor

```bash
cd /media/grishmin/Work/nepal-property-monitor

# Activate virtual environment
source .venv/bin/activate

# Run the monitor
python -m property_monitor
```

### 2. What Happens on First Run

The monitor will:
1. **Initialize**: Scrape current properties and save them as a baseline
2. **Print**: `✅ Initialized with X properties. Monitoring started.`
3. **Not notify**: No Discord messages on first run (prevents spam)
4. **Start monitoring**: Check every 15 minutes for new properties

### 3. What Happens on Subsequent Runs

Every 15 minutes:
1. Scrape Nepal Property Bazaar
2. Find NEW properties (not in database + posted < 24h + ≤ Rs 10,000)
3. Send Discord notifications with rich embeds
4. Update database

### 4. Manual Testing (Before Long Run)

To test without waiting 15 minutes:

```bash
# Test scraping (shows live data)
python test_scraper.py

# Test Discord webhook
python test_webhook.py

# Test full system (one cycle)
python test_e2e.py

# Check health
python scripts/health_check.py
```

## 📊 Sample Output

When running, you'll see:

```
[2025-11-08T11:29:12Z] [info] service_starting
[2025-11-08T11:29:14Z] [info] properties_found count=21
[2025-11-08T11:29:14Z] [info] properties_parsed count=16
[2025-11-08T11:29:14Z] [info] initialization_complete

✅ Initialized with 16 properties. Monitoring started.

📊 Stats: Total: 16 | New: 0 | Budget: 1 | Notifications: 0 | Duration: 2493ms

[2025-11-08T11:29:14Z] [info] sleeping seconds=910
```

## 🔔 Discord Notifications

When a new property is found, you'll receive a notification like:

```
🏠 NEW PROPERTY FOUND!

**1BHK Flat Rent in Imadol, Lalitpur**

🔥 URGENT - GREAT DEAL!

💰 Price: Rs 9,000/Month
📍 Location: Imadol, Lalitpur
🛏️ Bedrooms: 1
🚿 Bathrooms: 1
🏠 Type: Flat / Apartment
🕐 Posted: 25 minutes ago

🔗 View Details: [Click here]
```

Priority levels:
- 🔥 **URGENT** - Under Rs 7,000
- ⭐ **HIGH PRIORITY** - Rs 7,000-9,000
- ✓ **Within Budget** - Rs 9,000-10,000

## ⚙️ Configuration

Edit `.env` to customize:

```bash
# Budget filter (default: 10000)
PROPMON_MAX_PRICE=10000

# Check interval (default: 900 = 15 minutes)
PROPMON_SCRAPE_INTERVAL_SECONDS=900

# Time window for "new" properties (default: 24 hours)
PROPMON_TIME_WINDOW_HOURS=24

# Logging level
PROPMON_LOG_LEVEL=INFO
```

## 🛠️ Running in Production

### Option 1: Screen/Tmux (Simple)

```bash
screen -S property-monitor
python -m property_monitor
# Press Ctrl+A then D to detach

# Reattach later
screen -r property-monitor
```

### Option 2: Systemd Service (Recommended)

```bash
# Edit the service file with your username and paths
nano scripts/systemd/property-monitor.service

# Install service
sudo cp scripts/systemd/property-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable property-monitor
sudo systemctl start property-monitor

# Check status
sudo systemctl status property-monitor

# View logs
sudo journalctl -u property-monitor -f
```

## 📈 Monitoring

### View Database

```bash
python -c "import sqlite3; conn=sqlite3.connect('data/properties.db'); \
cursor=conn.execute('SELECT id, title, price FROM properties WHERE price <= 10000 ORDER BY price'); \
print('\\n'.join([f\"{r[0]}: {r[1]} - Rs {r[2]:,}\" for r in cursor.fetchall()]))"
```

### Health Check

```bash
python scripts/health_check.py
```

### View Logs

```bash
# If using systemd
sudo journalctl -u property-monitor -f

# Otherwise
tail -f property_monitor.log
```

## 🐛 Troubleshooting

### No new properties appearing?

This is **normal** on the first run! The system:
1. Saves all current properties as baseline
2. Only notifies about properties added **after** initialization
3. Checks timestamps (must be posted within last 24 hours)

**Solution**: Wait for the next scraping cycle (15 min) or wait for genuinely new properties to be posted.

### Want to simulate a new property?

```bash
# Delete one property from database to trigger re-detection
python -c "import sqlite3; conn=sqlite3.connect('data/properties.db'); \
conn.execute('DELETE FROM properties WHERE id=\"61473\" LIMIT 1'); \
conn.commit(); print('Property deleted. Will be re-detected on next run.')"

# Run another check
python test_e2e.py
```

### Discord notifications not sending?

1. Check webhook URL in `.env`
2. Test with: `python test_webhook.py`
3. Check rate limiting in logs

## 📚 Next Steps

1. **Run the monitor**: `python -m property_monitor`
2. **Let it initialize**: Wait for "Initialized with X properties" message
3. **Press Ctrl+C** to stop (or let it run continuously)
4. **Check Discord**: You should have received test notifications earlier
5. **Wait for new properties**: The monitor will notify you when new listings appear

## 🎓 Understanding the Code

The codebase follows Clean Architecture principles:

```
src/property_monitor/
├── domain/           # Core business logic (pure Python)
│   ├── models.py     # Property, MonitorStats (Pydantic)
│   └── exceptions.py # Custom exceptions
├── adapters/         # External integrations
│   ├── scrapers/     # Nepal Bazaar scraper
│   ├── notifiers/    # Discord webhook
│   └── storage/      # SQLite storage
└── services/         # Business logic coordination
    └── monitor_service.py  # Core monitoring logic
```

**Key Design Patterns**:
- **Dependency Injection**: All components are injected (easy testing)
- **Protocol-Based**: Using Python Protocols instead of ABC
- **Type-Safe**: Full type hints with mypy strict mode
- **Error Handling**: Comprehensive with custom exceptions

## 📞 Support

For issues:
1. Check `README.md` for detailed troubleshooting
2. Review logs for error messages
3. Run health check: `python scripts/health_check.py`

## 🎉 You're All Set!

Your property monitor is ready to help you find the perfect rental in Nepal!

**Happy house hunting!** 🏠

---

Built with ❤️ using Python 3.10+, httpx, selectolax, pydantic, structlog, and SQLite.
