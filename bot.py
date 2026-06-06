import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TELEGRAM_TOKEN = "8901885854:AAE_rYNK1ouyKu2cOC2ia0WkU9_HiUzTA70"
GROQ_API_KEY = "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"

SYSTEM_PROMPT = """You are a Free Fire account listing title generator.

Generate EXACTLY ONE listing title in this format:
[GLOBAL PLAYABLE]💛LEVEL-{X}🔥{X} EMOTES💀{best bundle}🙇🏻{X}+ VAULT🤑{evo}🕺🏻{best weapon skin}🐉{skydive}☘️{special feature}👾REGION-[INDIA]

STRICT RULES:
- NEVER mention rank
- Level: read from profile/lobby screen
- Emotes: total count from EMOTE sidebar number
- Entry emotes: multiple → count e.g. "2 ENTRY EMOTE", single → name it. Mention in special feature
- Best Bundle: most impressive/rare outfit name
- Vault: ONLY the COLLECTION number from left sidebar of Fashion screen e.g. 193+ VAULT
- EVOs: multiple → count e.g. "3 EVO GUNS", single → name e.g. "GROZA EVO"
- Weapon skin: best/rarest weapon skin name
- Skydive: multiple → count e.g. "2 SKYDIVE", single → name it
- Special feature: NARUTO COLLAB, entry emotes, pet, PRIME level etc.
- Cannot see value → write N/A

Output ONLY the title. Nothing else."""

DESCRIBE_PROMPT = """Look at this Free Fire account screenshot carefully. List every detail you can see:
- Player level (exact number)
- Number of emotes (sidebar number next to EMOTE)
- Number of entry emotes if visible
- Bundle/outfit names (exact names)
- COLLECTION number from left sidebar in Fashion screen (this is vault count)
- EVO gun names or count
- Weapon skin names
- Skydive names or count
- Any special features (Naruto collab, Prime level, pets etc.)

Be very specific with exact names and numbers. List everything you see."""

user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to FF Title Generator Bot!\n\n"
        "📸 Send screenshots one by one\n"
        "Then /generate to get your title!\n"
        "Send /clear to start fresh."
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

def call_groq_single(b64_image, prompt_text, system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
            {"type": "text", "text": prompt_text}
        ]
    })
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.1
        },
        timeout=60
    )
    data = response.json()
    if "choices" not in data:
        raise Exception(data.get("error", {}).get("message", str(data)))
    return data["choices"][0]["message"]["content"].strip()

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    images = user_images.get(user_id, [])

    if not images:
        await update.message.reply_text("❌ No screenshots! Send FF account screenshots first.")
        return

    await update.message.reply_text(f"🔍 Reading {len(images)} screenshot(s) one by one... Please wait!")

    try:
        if len(images) == 1:
            # Single image - generate title directly
            title = call_groq_single(images[0], "Generate the Free Fire listing title from this screenshot.", SYSTEM_PROMPT)
        else:
            # Multiple images - describe each one, then combine into title
            descriptions = []
            for i, img in enumerate(images):
                await update.message.reply_text(f"📖 Reading screenshot {i+1}/{len(images)}...")
                desc = call_groq_single(img, DESCRIBE_PROMPT)
                descriptions.append(f"Screenshot {i+1}:\n{desc}")

            # Now generate title from all descriptions
            combined = "\n\n".join(descriptions)
            final_prompt = f"Based on these FF account screenshot descriptions, generate the listing title:\n\n{combined}"
            title = call_groq_single(
                images[0],  # Send first image as context
                final_prompt,
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
