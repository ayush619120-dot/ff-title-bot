import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TELEGRAM_TOKEN = "8901885854:AAE_rYNK1ouyKu2cOC2ia0WkU9_HiUzTA70"
GROQ_API_KEY = "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"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM_PROMPT = """You are a Free Fire account listing title generator.

Generate EXACTLY ONE listing title in this format:
[GLOBAL PLAYABLE]💛LEVEL-{X}🔥{X} EMOTES💀{best bundle}🙇🏻{X}+ VAULT🤑{evo}🕺🏻{best weapon skin}🐉{skydive}☘️{special feature}👾REGION-[INDIA]

RULES:
- NEVER mention rank
- Level: number shown on profile (Lv.XX)
- Emotes: the small number next to EMOTE label in the left sidebar of the vault/fashion screen
- Best Bundle: most impressive outfit/bundle name shown on character
- Vault: the number next to COLLECTION in the LEFT SIDEBAR of the Fashion/Vault screen. NEVER use the Gallery ALL count. NEVER use any other number. It is labeled "COLLECTION" on the left side menu.
- EVOs: guns with EVO label → multiple = "3 EVO GUNS", single = name it e.g. "GROZA EVO". No EVO = "NO EVO"
- Best weapon skin: the most impressive named weapon skin from armory screen
- Skydive: multiple = "2 SKYDIVE", single = name it. Not visible = N/A
- Special feature: collab (Naruto etc), 6 YEARS OLD badges, entry emotes, pet, PRIME level etc
- Only use N/A if truly not visible in any screenshot

Output ONLY the title. Nothing else."""

DESCRIBE_PROMPT = """Analyze this Free Fire account screenshot carefully. Extract ONLY what is clearly visible:

LEVEL: Look for "Lv.XX" text on profile card or top left
EMOTE COUNT: The number shown next to "EMOTE" text in the LEFT SIDEBAR (not the emote grid count)
BUNDLE NAME: The outfit/bundle name shown below the character preview (exact text)
COLLECTION COUNT (VAULT): The number shown next to "COLLECTION" in the LEFT SIDEBAR of the Fashion screen. THIS IS NOT the Gallery ALL number. It is specifically the "COLLECTION" row in the sidebar.
EVO GUNS: Any weapon with "EVO" in its name or an EVO badge/label
WEAPON SKINS: Exact weapon skin names shown in Armory (e.g. "P90 - GILDED CORROSION", "SCAR - CUPID")
SKYDIVE: Any skydive skin names visible
SPECIAL FEATURES: Naruto collab items, "6 YEARS OLD" badges, pets, Prime level, entry emotes

Report ONLY what you can clearly read. Say "not visible" for anything unclear."""

user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 FF Title Generator Bot!\n\n"
        "📸 Send screenshots ONE BY ONE\n"
        "✅ Then /generate\n"
        "🗑️ /clear to start fresh"
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
            all_info = []
            for i, img in enumerate(images):
                desc = groq_call(img, DESCRIBE_PROMPT)
                all_info.append(f"[Screenshot {i+1}]:\n{desc}")

            combined = "\n\n".join(all_info)
            title = groq_call(
                images[0],
                f"Here are descriptions of {len(images)} FF account screenshots:\n\n{combined}\n\n"
                f"IMPORTANT REMINDER:\n"
                f"- VAULT = the number next to COLLECTION in left sidebar of Fashion screen (NOT Gallery ALL count)\n"
                f"- EMOTES = number next to EMOTE in left sidebar\n"
                f"- Only name EVOs if they have EVO label\n"
                f"- Use the best weapon skin name from armory\n\n"
                f"Now generate the listing title.",
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
