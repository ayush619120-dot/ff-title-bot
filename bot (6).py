import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TELEGRAM_TOKEN = "8901885854:AAE_rYNK1ouyKu2cOC2ia0WkU9_HiUzTA70"
GEMINI_API_KEY = "AQ.Ab8RN6IL97k2FBeMLplRc6LoiZIgU8dE74McR9uAjwk_0UfRgQ"

SYSTEM_PROMPT = """You are a Free Fire account listing title generator. The user will send you one or more screenshots of a Free Fire account.

Generate EXACTLY ONE listing title in this format:
[GLOBAL PLAYABLE]💛LEVEL-{X}🔥{X} EMOTES💀{best bundle}🙇🏻{X}+ VAULT🤑{evo}🕺🏻{best weapon skin}🐉{skydive}☘️{special feature}👾REGION-[INDIA]

STRICT RULES:
- NEVER mention rank
- Level: read from profile/lobby screen
- Emotes: count total emotes from emote screen (the number shown next to EMOTE in sidebar)
- Entry emotes: If multiple entry emotes → write count e.g. "2 ENTRY EMOTE". If only 1 → name it. Always mention in special feature
- Best Bundle: pick the most impressive/rare outfit name visible
- Vault count: use ONLY the COLLECTION number from the left sidebar of the Fashion screen. Format: e.g. 193+ VAULT
- EVOs: If multiple EVO guns → write count only e.g. "3 EVO GUNS". If only 1 EVO gun → write its name e.g. "GROZA EVO"
- Weapon skin: name the best/rarest weapon skin visible
- Skydive: If multiple skydives → count only e.g. "2 SKYDIVE". If only 1 → name it
- Special feature: mention notable things like NARUTO COLLAB, entry emotes, pet, PRIME level etc.
- If you cannot clearly see a value write N/A

Output ONLY the title string. No explanation, no preamble, nothing else."""

user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to FF Title Generator Bot!\n\n"
        "📸 Send me screenshots one by one\n"
        "Then send /generate to get your listing title!\n"
        "Send /clear to start fresh for a new account."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_images:
        user_images[user_id] = []

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    user_images[user_id].append(b64)

    count = len(user_images[user_id])
    await update.message.reply_text(f"✅ Screenshot {count} saved! Send more or /generate when ready.")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    images = user_images.get(user_id, [])

    if not images:
        await update.message.reply_text("❌ No screenshots! Send FF account screenshots first.")
        return

    await update.message.reply_text(f"🔍 Analyzing {len(images)} screenshot(s)... Please wait!")

    try:
        parts = []
        for b64 in images:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64
                }
            })
        parts.append({
            "text": SYSTEM_PROMPT + "\n\nGenerate the Free Fire account listing title from these screenshots. Output ONLY the title."
        })

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": parts}]},
            timeout=60
        )

        data = response.json()

        if "candidates" not in data:
            error = data.get("error", {}).get("message", str(data))
            await update.message.reply_text(f"❌ API Error: {error}")
            return

        title = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        await update.message.reply_text(f"🎮 Your listing title:\n\n`{title}`", parse_mode="Markdown")
        user_images[user_id] = []
        await update.message.reply_text("✅ Done! Send new screenshots for next account.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}\n\nTry /clear and restart.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_images[user_id] = []
    await update.message.reply_text("🗑️ Cleared! Send screenshots for new account.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
