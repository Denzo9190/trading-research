# Telegram Intelligence

Research module for collecting and analyzing trading ideas from Telegram crypto trading channels.

Part of TradingLab research infrastructure.

## Features

- Telegram channel parsing (Telethon) – public/private channels, IDs, invite links
- Message storage in SQLite (~180k messages collected)
- Idea extraction (RU/EN) – asset, direction, level, target
- Channel ranking by ideas density, activity, freshness
- TradingView alert relay via email (Gmail/IMAP)
- Interactive Telegram bot with inline buttons (Yes/No/Skip/Pause/Resume)
- Timeouts, screenshot attachment, global pause

## Architecture
Telegram → Parser → Messages DB → Idea Extractor → Ideas DB → Channel Ranking
TradingView → Email Listener → Pending Alerts DB → Alert Handler → Telegram Bot → Channel

## Setup

1. Clone repository.
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your credentials:
    - Telegram API ID / Hash
    - Telegram Bot Token
    - Target channel ID/username
    - Your admin user ID
    - Email address and app password (for Gmail)
6. Run:
    - `python parser.py` (collect messages)
    - `python extractor.py` (extract ideas)
    - `python rank_channels.py` (get ranking)
    - `python tv_alert_relay/tv_alert_handler.py` (start bot)
    - `python email_listener.py` (start email listener)

## Data

- SQLite database: `tg_messages.db`
- Tables: `messages`, `ideas`, `pending_alerts`, `settings`

## Status

Version: v0.1

- Channels tracked: ~375
- Messages collected: ~180k
- Ideas extracted: ~15k
- Alert relay: operational

## Next Steps (v0.2)

- Pattern detection (liquidity clusters, breakout, retest)
- Idea accuracy engine (validate ideas against market data)
- Weekly intelligence reports