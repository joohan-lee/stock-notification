# Product Requirements Document (PRD)

## Overview

**Product Name**: Modo (Latin for "just now" / "바로 지금")

**Why Modo?**: 주식을 사고 팔아야 할 순간을 놓치지 않기 위해. "바로 지금"이 중요한 순간에 알림을 받아 기회를 잡는다.

**Purpose**: Monitor US stocks and ETFs, and send alerts based on predefined and custom rules when specific conditions are met.

**Target User**: Individual investors who want to be notified of significant price movements without constantly watching the market.

**Design Principle**: Built for personal use first, but architected to support multiple users in the future.

---

## Problem Statement

Individual investors often miss important market movements because:
- They cannot monitor the market 24/7
- Manual price checking is tedious and error-prone
- Existing solutions are either too expensive or too complex

---

## Goals

1. Provide automated monitoring of US stocks and ETFs
2. Alert users when stocks drop from monthly highs (-5%, -10%, etc.)
3. Detect unusual market activity (volume spikes, sudden price changes)
4. Allow users to define custom alert rules
5. Deliver notifications via Discord and Email

---

## User Stories

### US-1: Monthly High Drop Alert
**As** an investor,
**I want** to be notified when a stock drops X% from its monthly high,
**So that** I can consider buying opportunities during dips.

**Acceptance Criteria**:
- System tracks 30-day rolling high for each monitored symbol
- Alert triggers when current price drops 5%, 10%, 15%, or 20% from the high
- Alert includes: symbol, current price, monthly high, drop percentage

### US-2: Daily Price Surge/Drop Alert
**As** an investor,
**I want** to be notified when a stock moves more than X% in a single day,
**So that** I can react to significant market events.

**Acceptance Criteria**:
- Alert triggers when daily change exceeds configured threshold (default: ±5%)
- Alert includes: symbol, current price, previous close, change percentage

### US-3: Volume Spike Alert
**As** an investor,
**I want** to be notified when trading volume is unusually high,
**So that** I can investigate potential catalysts.

**Acceptance Criteria**:
- System calculates 20-day average volume
- Alert triggers when current volume exceeds N times the average (default: 3x)
- Alert includes: symbol, current volume, average volume, multiplier

### US-4: Custom Rules
**As** an advanced user,
**I want** to define my own alert rules,
**So that** I can monitor specific conditions relevant to my strategy.

**Acceptance Criteria**:
- Users can add custom rules via configuration file
- Rules support basic conditions (price above/below, percentage change, etc.)

### US-5: Multi-Channel Notifications
**As** a user,
**I want** to receive alerts via Discord and/or Email,
**So that** I can choose my preferred notification method.

**Acceptance Criteria**:
- Discord notifications via webhook
- Email notifications via SMTP
- Users can enable/disable each channel independently

---

## Scope

### In Scope (MVP)
- Monitor US stocks and ETFs via Yahoo Finance
- Fetch and store complete symbol list from API
- User watchlist management (select symbols to monitor)
- Predefined rules: monthly high drop, daily change, volume spike
- Custom rules support
- Notifications: Discord webhook, Email (SMTP)
- SQLite database for:
  - Symbol master data
  - User watchlists and settings
  - Alert history (deduplication)
- Docker deployment on Oracle Cloud
- Hourly or daily check frequency

### Out of Scope (Future)
- Web UI for configuration
- Real-time price monitoring
- Korean stocks (KOSPI, KOSDAQ)
- Cryptocurrency
- Push notifications (mobile)
- Multi-user authentication system

---

## Success Metrics

1. **Reliability**: 99%+ uptime on Oracle Cloud
2. **Latency**: Alerts sent within 5 minutes of condition being met
3. **Accuracy**: Zero false negatives (missed alerts)

---

## Timeline

| Phase | Description |
|-------|-------------|
| Phase 1 | Core functionality (data fetching, rule engine, Discord notification) |
| Phase 2 | Email notification, configuration validation |
| Phase 3 | Docker setup, deployment to Oracle Cloud |
| Phase 4 | Testing, documentation, refinement |
