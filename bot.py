import os
import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TELEGRAM_TOKEN = "8901885854:AAE_rYNK1ouyKu2cOC2ia0WkU9_HiUzTA70"
GROQ_API_KEY = "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"

SYSTEM_PROMPT = """You are a Free Fire account listing title generator. The user will send you one or more screenshots of a Free Fire account.

Generate EXACTLY ONE listing title in this format:
[GLOBAL PLAYABLE]💛LEVEL-{X}🔥{X} EMOTES💀{best bundle}🙇🏻{X}+ VAULT🤑{evo}🕺🏻{best weapon skin}🐉{skydive}☘️{special feature}👾REGION-[INDIA]

STRICT RULES:
- NEVER mention rank
- Level: read from profile/lobby screen
- Emotes: count total emotes from emote screen (the number shown next to EMOTE in sidebar)
- Entry emotes: If multiple entry emotes → write count e.g. "2 ENTRY EMOTE". If only 1 → name it. Always mention entry emotes in special feature if present
- Best Bundle: pick the most impressive/rare outfit name visible
- Vault count: use ONLY the COLLECTION number from the left sidebar of the Fashion screen. Format: e.g. 193+ VAULT
- EVOs: If multiple EVO guns → write count only e.g. "3 EVO GUNS". If only 1 EVO gun → write its name e.g. "GROZA EVO". Look carefully at armory and profile weapon section
- Weapon skin: name the best/rarest weapon skin visible
- Skydive: If multiple skydives → count only e.g. "2 SKYDIVE". If only 1 → name it e.g. "WINGED SKYDIVE"
- Special feature: mention notable things like NARUTO COLLAB, entry emotes, pet, character, PRIME level etc.
- If you cannot clearly see a value, make a reasonable estimate or write N/A

Output ONLY the title string. No explanation, no preamble, nothing else."""

# Store images per user session
user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to FF Title Generator Bot!\n\n"
        "📸 Send me screenshots of the FF account (lobby, fashion, emotes, armory, skydive etc.)\n\n"
        "Then send /generate and I'll create your listing title!\n\n"
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
    await update.message.reply_text(f"✅ Screenshot {count} received! Send more or type /generate when ready.")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    images = user_images.get(user_id, [])

    if not images:
        await update.message.reply_text("❌ No screenshots received yet! Please send your FF account screenshots first.")
        return

    await update.message.reply_text(f"🔍 Analyzing {len(images)} screenshot(s)... Please wait!")

    try:
        content = []
        for b64 in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}"
                }
            })
        content.append({
            "type": "text",
            "text": "Generate the Free Fire account listing title from these screenshots."
        })

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            },
            timeout=60
        )

        data = response.json()
        title = data["choices"][0]["message"]["content"].strip()

        await update.message.reply_text(f"🎮 Your listing title:\n\n`{title}`", parse_mode="Markdown")
        user_images[user_id] = []
        await update.message.reply_text("✅ Screenshots cleared! Send new screenshots for next account.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}\n\nTry again or send /clear and restart.")

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
