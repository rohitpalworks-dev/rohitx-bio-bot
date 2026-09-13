
import os
import io
import logging
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

(
    NAME,
    IDENTITY,
    BIO,
    SKILLS,
    TELEGRAM,
    INSTAGRAM,
    GITHUB,
    THEME,
) = range(9)

THEMES = {
    "ocean": {
        "label": "🌊 Ocean",
        "primary": "#22b9ff",
        "secondary": "#4f7cff",
        "accent": "#6ee7ff",
        "bg1": "#020617",
        "bg2": "#071b31",
    },
    "purple": {
        "label": "💜 Neon Purple",
        "primary": "#a855f7",
        "secondary": "#6366f1",
        "accent": "#d8b4fe",
        "bg1": "#090516",
        "bg2": "#160d2d",
    },
    "midnight": {
        "label": "🌌 Midnight",
        "primary": "#60a5fa",
        "secondary": "#334155",
        "accent": "#93c5fd",
        "bg1": "#02040a",
        "bg2": "#0a1020",
    },
    "emerald": {
        "label": "🌿 Emerald",
        "primary": "#22c55e",
        "secondary": "#0ea5a4",
        "accent": "#86efac",
        "bg1": "#02100a",
        "bg2": "#06251c",
    },
    "sunset": {
        "label": "🔥 Sunset",
        "primary": "#ff7a18",
        "secondary": "#e11d48",
        "accent": "#ffd166",
        "bg1": "#120704",
        "bg2": "#27100a",
    },
}

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{NAME}} | Bio</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
--primary:{{PRIMARY}};
--secondary:{{SECONDARY}};
--accent:{{ACCENT}};
--bg1:{{BG1}};
--bg2:{{BG2}};
--card:rgba(10,20,35,.60);
--border:rgba(255,255,255,.14);
--text:#fff;
--muted:#b7c1d3
}
html,body{min-height:100%}
body{
min-height:100vh;
font-family:Arial,Helvetica,sans-serif;
color:var(--text);
background:
radial-gradient(circle at 20% 20%,color-mix(in srgb,var(--primary) 28%,transparent),transparent 28%),
radial-gradient(circle at 80% 25%,color-mix(in srgb,var(--secondary) 26%,transparent),transparent 30%),
radial-gradient(circle at 50% 90%,color-mix(in srgb,var(--accent) 15%,transparent),transparent 25%),
linear-gradient(135deg,var(--bg1),var(--bg2));
overflow-x:hidden;
}
body:before{
content:"";position:fixed;width:700px;height:700px;left:-200px;top:-250px;
background:radial-gradient(circle,color-mix(in srgb,var(--primary) 28%,transparent),transparent 65%);
filter:blur(60px);animation:a1 12s ease-in-out infinite alternate;z-index:-4
}
body:after{
content:"";position:fixed;width:650px;height:650px;right:-230px;bottom:-200px;
background:radial-gradient(circle,color-mix(in srgb,var(--secondary) 25%,transparent),transparent 65%);
filter:blur(75px);animation:a2 15s ease-in-out infinite alternate;z-index:-4
}
@keyframes a1{0%{transform:translate(0,0) scale(1)}50%{transform:translate(90px,100px) scale(1.15)}100%{transform:translate(30px,170px) scale(.9)}}
@keyframes a2{0%{transform:translate(0,0) scale(1)}50%{transform:translate(-100px,-80px) scale(1.15)}100%{transform:translate(-40px,-160px) scale(.9)}}
.wind{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:-2}
.wind span{
position:absolute;width:160px;height:1px;border-radius:50%;
background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--accent) 75%,white),transparent);
opacity:0;transform:rotate(-18deg);animation:w linear infinite
}
.wind span:nth-child(1){top:12%;left:-220px;animation-duration:7s}
.wind span:nth-child(2){top:28%;left:-300px;animation-duration:5s;animation-delay:2s}
.wind span:nth-child(3){top:42%;left:-240px;animation-duration:8s;animation-delay:1s}
.wind span:nth-child(4){top:60%;left:-320px;animation-duration:6s;animation-delay:3s}
.wind span:nth-child(5){top:74%;left:-250px;animation-duration:7s;animation-delay:1.5s}
.wind span:nth-child(6){top:87%;left:-300px;animation-duration:5.5s;animation-delay:2.5s}
@keyframes w{0%{transform:translateX(0) rotate(-18deg);opacity:0}15%{opacity:.45}70%{opacity:.35}100%{transform:translateX(135vw) rotate(-18deg);opacity:0}}
.wrapper{min-height:100vh;display:flex;justify-content:center;align-items:center;padding:40px 15px}
.card{
width:100%;max-width:430px;padding:32px 25px;border-radius:28px;background:var(--card);
border:1px solid var(--border);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
box-shadow:0 25px 80px rgba(0,0,0,.48),inset 0 1px 0 rgba(255,255,255,.07)
}
.profile{text-align:center}
.photo{width:108px;height:108px;object-fit:cover;border-radius:50%;border:3px solid var(--accent);
box-shadow:0 0 0 5px color-mix(in srgb,var(--primary) 15%,transparent),0 0 35px color-mix(in srgb,var(--primary) 40%,transparent);margin-bottom:15px}
.name{font-size:34px;font-weight:800;letter-spacing:.5px}
.tag{margin-top:6px;color:var(--accent);font-size:14px}
.intro{max-width:340px;margin:16px auto 28px;color:var(--muted);font-size:14px;line-height:1.7}
.section{margin-top:25px}
.title{display:flex;align-items:center;gap:10px;font-size:18px;margin-bottom:12px}
.title:after{content:"";height:1px;flex:1;background:linear-gradient(90deg,var(--primary),transparent);opacity:.5}
.about{padding:15px;border-radius:15px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);color:var(--muted);font-size:14px;line-height:1.8}
.about b{color:#fff}
.skills{display:flex;flex-wrap:wrap;justify-content:center;gap:9px}
.skill{padding:9px 13px;border-radius:20px;background:rgba(255,255,255,.065);border:1px solid rgba(255,255,255,.09);font-size:12px}
.links{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.link{padding:13px;border-radius:13px;text-align:center;text-decoration:none;color:#fff;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);font-size:13px}
.footer{text-align:center;margin-top:25px;color:#7c8799;font-size:10px;letter-spacing:1px}
@media(max-width:500px){.card{padding:30px 20px}.name{font-size:30px}}
</style>
</head>
<body>
<div class="wind"><span></span><span></span><span></span><span></span><span></span><span></span></div>
<div class="wrapper">
<div class="card">
<div class="profile">
<img class="photo" src="{{PHOTO}}" alt="Profile">
<div class="name">{{NAME}}</div>
<div class="tag">{{IDENTITY}}</div>
<div class="intro">{{BIO}}</div>
</div>
<div class="section">
<div class="title">About Me</div>
<div class="about">👋 Hey! I'm <b>{{NAME}}</b>.<br>{{BIO}}</div>
</div>
<div class="section">
<div class="title">Skills</div>
<div class="skills">{{SKILLS}}</div>
</div>
<div class="section">
<div class="title">Find Me</div>
<div class="links">
<a class="link" href="{{TELEGRAM}}" target="_blank">Telegram</a>
<a class="link" href="{{INSTAGRAM}}" target="_blank">Instagram</a>
<a class="link" href="{{GITHUB}}" target="_blank">GitHub</a>
<a class="link" href="mailto:{{EMAIL}}">Email</a>
</div>
</div>
<div class="footer">MADE WITH ✦ BY {{NAME}}</div>
</div>
</div>
</body>
</html>
"""


def profile_to_html(data: dict) -> str:
    theme = THEMES.get(data.get("theme", "ocean"), THEMES["ocean"])
    skills = []
    for s in data["skills"]:
        safe = escape(s.strip())
        if safe:
            skills.append(f'<div class="skill">{safe}</div>')

    html = TEMPLATE
    replacements = {
        "{{NAME}}": escape(data["name"]),
        "{{IDENTITY}}": escape(data["identity"]),
        "{{BIO}}": escape(data["bio"]),
        "{{PHOTO}}": escape(data["photo_url"]),
        "{{TELEGRAM}}": escape(data["telegram"]),
        "{{INSTAGRAM}}": escape(data["instagram"]),
        "{{GITHUB}}": escape(data["github"]),
        "{{EMAIL}}": escape(data.get("email", "")),
        "{{SKILLS}}": "\n".join(skills),
        "{{PRIMARY}}": theme["primary"],
        "{{SECONDARY}}": theme["secondary"],
        "{{ACCENT}}": theme["accent"],
        "{{BG1}}": theme["bg1"],
        "{{BG2}}": theme["bg2"],
    }
    for k, v in replacements.items():
        html = html.replace(k, v)
    return html


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🌐 Welcome to RohitX Bio Generator!\n\n"
        "I'll create a ready-to-use personal bio website for you.\n\n"
        "Let's start.\n\n"
        "👤 Send your name:"
    )
    return NAME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Send /start to create a new website.")
    return ConversationHandler.END


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()[:60]
    await update.message.reply_text("✨ Now send your identity / role.\nExample: Student • Creator • Developer")
    return IDENTITY


async def get_identity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["identity"] = update.message.text.strip()[:120]
    await update.message.reply_text("📝 Write a short bio about yourself.")
    return BIO


async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bio"] = update.message.text.strip()[:350]
    await update.message.reply_text(
        "🧩 Send your skills separated by commas.\n\n"
        "Example:\nPython, AI, Web Development, Editing"
    )
    return SKILLS


async def get_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["skills"] = [x.strip() for x in update.message.text.split(",") if x.strip()][:12]
    await update.message.reply_text(
        "🔗 Send your Telegram username or full link.\n"
        "Example: @rohitx"
    )
    return TELEGRAM


def normalize_link(value: str, kind: str) -> str:
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    value = value.lstrip("@").strip("/")
    if kind == "telegram":
        return f"https://t.me/{value}"
    if kind == "instagram":
        return f"https://instagram.com/{value}"
    return f"https://github.com/{value}"


async def get_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["telegram"] = normalize_link(update.message.text, "telegram")
    await update.message.reply_text(
        "📸 Send your Instagram username or full link."
    )
    return INSTAGRAM


async def get_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["instagram"] = normalize_link(update.message.text, "instagram")
    await update.message.reply_text(
        "💻 Send your GitHub username or full link."
    )
    return GITHUB


async def get_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["github"] = normalize_link(update.message.text, "github")
    await update.message.reply_text(
        "🎨 Choose a theme:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌊 Ocean", callback_data="theme:ocean"),
                InlineKeyboardButton("💜 Purple", callback_data="theme:purple"),
            ],
            [
                InlineKeyboardButton("🌌 Midnight", callback_data="theme:midnight"),
                InlineKeyboardButton("🌿 Emerald", callback_data="theme:emerald"),
            ],
            [
                InlineKeyboardButton("🔥 Sunset", callback_data="theme:sunset"),
            ],
        ])
    )
    return THEME


async def get_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    theme = query.data.split(":", 1)[1]
    context.user_data["theme"] = theme

    # Placeholder email; add your own email field later if desired.
    context.user_data["email"] = ""

    context.user_data["photo_url"] = DEFAULT_PHOTO
    html = profile_to_html(context.user_data)

    document = io.BytesIO(html.encode("utf-8"))
    document.name = "index.html"

    await query.message.reply_text("✅ Your website is ready!")
    await query.message.reply_document(
        document=document,
        caption=(
            "🌐 Your personal bio website is ready.\n\n"
            "Upload this file to GitHub as `index.html`, then enable GitHub Pages."
        ),
    )

    context.user_data.clear()
    return ConversationHandler.END


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing. "
            "Set your BotFather token as BOT_TOKEN."
        )

    app = Application.builder().token(token).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            IDENTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_identity)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
            SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_skills)],
            TELEGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_telegram)],
            INSTAGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_instagram)],
            GITHUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_github)],
            THEME: [CallbackQueryHandler(get_theme, pattern=r"^theme:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conversation)
    app.run_polling()


if __name__ == "__main__":
    main()
