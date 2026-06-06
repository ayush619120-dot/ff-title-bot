import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TELEGRAM_TOKEN = "8901885854:AAE_rYNK1ouyKu2cOC2ia0WkU9_HiUzTA70"
GROQ_API_KEY = "gsk_9cIxcf46N8WQLHsHhfwA7WGdyb3FY4lWwhameP1LkjMFYRwzl9tjB"
GROQ_API_KEY = "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"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM_PROMPT = """You are a Free Fire account listing title generator.

Generate EXACTLY ONE listing title in this format:
[GLOBAL PLAYABLE]💛LEVEL-{X}🔥{X} EMOTES💀{best bundle}🙇🏻{X}+ VAULT🤑{evo}🕺🏻{best weapon skin}🐉{skydive}☘️{special feature}👾REGION-[INDIA]

RULES:
- NEVER mention rank
- Level: number shown on profile/lobby
- Emotes: number next to EMOTE in sidebar
- Entry emotes: multiple → "2 ENTRY EMOTE", single → name it
- Best Bundle: most impressive outfit/bundle name
- Vault: ONLY the COLLECTION number from left sidebar in Fashion screen e.g. 193+ VAULT
- EVOs: multiple → "3 EVO GUNS", single → name e.g. "GROZA EVO"
- Weapon skin: best weapon skin name visible in armory
- Skydive: multiple → "2 SKYDIVE", single → name it
- Special feature: collab, entry emotes, pet, PRIME level etc.
- Cannot see value → use best guess from other screenshots, only use N/A as last resort

Output ONLY the title. Nothing else."""

user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 FF Title Generator Bot!\n\n"
        "📸 Send screenshots ONE BY ONE (not as album)\n"
        "✅ Then /generate to get your title!\n"
        "🗑️ /clear to start fresh."
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

def groq_call(b64_image, user_text, system_text=None):
    messages = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
            {"type": "text", "text": user_text}
        ]
    })
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "max_tokens": 500, "temperature": 0.1},
        timeout=60
    )
    data = r.json()
    if "choices" not in data:
        raise Exception(data.get("error", {}).get("message", str(data)))
    return data["choices"][0]["message"]["content"].strip()

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    images = user_images.get(user_id, [])
    if not images:
        await update.message.reply_text("❌ No screenshots! Send FF account screenshots first.")
        return

    await update.message.reply_text(f"🔍 Reading {len(images)} screenshot(s)... Please wait!")

    try:
        if len(images) == 1:
            title = groq_call(images[0], "Generate the Free Fire listing title from this screenshot.", SYSTEM_PROMPT)
        else:
            # Step 1: describe each screenshot with targeted questions
            all_info = []
            for i, img in enumerate(images):
                desc = groq_call(img, 
                    "Look at this Free Fire screenshot very carefully. Tell me EXACTLY:\n"
                    "1. Player LEVEL (exact number from top left)\n"
                    "2. EMOTES count (number next to EMOTE in left sidebar)\n"
                    "3. ENTRY EMOTES count and names if visible\n"
                    "4. BUNDLE/OUTFIT names (exact text shown)\n"
                    "5. COLLECTION number from left sidebar (vault count)\n"
                    "6. EVO GUN names (look for EVO label on weapons)\n"
                    "7. WEAPON SKIN names (exact names shown in armory)\n"
                    "8. SKYDIVE names or count\n"
                    "9. Special features (Naruto collab, Prime level, pets, etc.)\n"
                    "Only report what you can actually see. Be specific with exact names and numbers."
                )
                all_info.append(f"[Screenshot {i+1}]: {desc}")

            # Step 2: generate title from all collected info
            combined = "\n\n".join(all_info)
            title = groq_call(
                images[0],
                f"Here are details from {len(images)} Free Fire account screenshots:\n\n{combined}\n\nNow generate the listing title using ALL the information above.",
                SYSTEM_PROMPT
            )

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
