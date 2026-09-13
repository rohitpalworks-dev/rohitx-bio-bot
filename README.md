
# RohitX Bio Generator Bot

A simple Telegram bot that collects a user's identity, bio, skills, profile photo, social links and theme, then generates a ready-to-upload `index.html`.

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Set the bot token

Create a bot with BotFather, then set:

```bash
BOT_TOKEN=YOUR_TOKEN
```

Windows PowerShell:
```powershell
$env:BOT_TOKEN="YOUR_TOKEN"
```

Linux/macOS:
```bash
export BOT_TOKEN="YOUR_TOKEN"
```

## 3. Run

```bash
python bot.py
```

## 4. Important note about profile photos

This starter version uses Telegram's file path as the image URL. For a production deployment, upload the photo to object storage (for example Cloudflare R2, S3-compatible storage, or another public image host) and store the resulting public URL.

## 5. Generated website

The bot sends a file named `index.html`. Upload it to a GitHub repository and enable GitHub Pages.
