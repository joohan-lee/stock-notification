# Modo TODO

## High Priority

### Email Notification Setup
- [ ] Configure SMTP settings in `config.yaml`
- [ ] Add SMTP credentials to `.env`:
  ```
  SMTP_USER=your-email@gmail.com
  SMTP_PASSWORD=your-app-password
  ```
- [ ] Update user with email address:
  ```bash
  sqlite3 data/modo.db "UPDATE users SET email = 'your-email@example.com' WHERE id = 1;"
  ```
- [ ] Test email notification

## Medium Priority

### Consolidate Rules
- [ ] Merge duplicate monthly_high_drop rules (ID 1 and 4) into one:
  ```bash
  sqlite3 data/modo.db "UPDATE user_rules SET parameters = '{\"thresholds\": [-3, -5, -10, -15, -20]}' WHERE id = 1;"
  sqlite3 data/modo.db "DELETE FROM user_rules WHERE id = 4;"
  ```

### CLI Improvements
- [ ] Add `rules list` command to view current rules
- [ ] Add `rules delete` command
- [ ] Add `watchlist remove` command
- [ ] Add `symbols add` command for manual symbol addition (mutual funds)

## Low Priority

### Features
- [ ] Add volume spike rule to watchlist
- [ ] Add Slack notification support
- [ ] Web UI for configuration

### Documentation
- [ ] Add troubleshooting section for email setup
- [ ] Add Gmail App Password setup guide

---

## Current Status

**Completed:**
- [x] Core implementation
- [x] Discord notification working
- [x] Symbol sync (12,222 symbols)
- [x] User created with Discord webhook
- [x] Watchlist: DIA, SPY, QQQM, FXAIX
- [x] Rules configured:
  - Monthly high drop: -3%, -5%, -10%, -15%, -20%
  - Daily change: ±3%, +5%
  - Monthly low rise: +5%, +10%
- [x] README.md
- [x] User Guide
- [x] Mutual fund manual addition documented
- [x] Oracle Cloud deployment (uv + Python 3.13)
- [x] Cron-based scheduled execution (hourly alert check)
- [x] Weekly healthcheck via cron

**Not Started:**
- [ ] Email notification
