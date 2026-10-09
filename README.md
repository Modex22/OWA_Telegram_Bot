# OWA! Telegram Bot

A starter Telegram bot for saving personal bus stops and receiving proximity alerts.

## Features
- `/start` sends a welcome message with inline buttons.
- The Telegram **Menu** button lists `/start`, `/journey`, `/addstop`, `/stops`, `/stop`, `/help`.
- Save a stop by naming it and sharing its map pin.
- Choose a destination, then share Telegram Live Location while travelling.
- Alerts at about 1,000 m, 500 m, 150 m and 60 m.

## Important
- No paid map/location API is used.
- Distances are straight-line GPS distances, not road distances.
- The bot needs Telegram location updates while Live Location sharing is active.
- Railway's local filesystem can be ephemeral. Add a persistent volume and set `DATABASE_PATH=/data/owa.db` if you need saved stops to survive redeploys.
- Test real journeys before relying on it. GPS and Telegram/iOS background behaviour can affect alerts.

## Run locally
1. Install Python 3.10+.
2. Create a bot with @BotFather and copy the token.
3. `python -m venv .venv`
4. Windows: `.venv\\Scripts\\Activate.ps1` (PowerShell); macOS/Linux: `source .venv/bin/activate`
5. `pip install -r requirements.txt`
6. PowerShell: `$env:BOT_TOKEN="YOUR_TOKEN"`; macOS/Linux: `export BOT_TOKEN="YOUR_TOKEN"`
7. `python bot.py`

## Railway
1. Push these files to GitHub.
2. Deploy the repository on Railway.
3. Add Railway variable `BOT_TOKEN` with your BotFather token.
4. Set start command to `python bot.py`.
5. Check deploy logs.
6. Do not run another copy of the same bot token locally while Railway is polling.

## Save and use a stop
1. Tap **📍 Add a bus stop** and send a name.
2. Attach -> Location -> send a regular location pin for the stop.
3. Tap **🚌 Start journey** and choose the saved stop.
4. Attach -> Location -> **Share Live Location** during the journey.
