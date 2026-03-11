import discord
import os
import datetime
import pytz
import requests
import json
import asyncio
from groq import Groq
from discord.ext import commands, tasks

# --- 🔒 ข้อมูลความปลอดภัย (ผู้สร้าง: นายท่านน้ำมนต์ / Harubito Honami) ---
OWNER_ID = 841691286125019186 
LOG_CHANNEL_ID = 1299667544814391349
MUSIC_PATH = "./music"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบฐานข้อมูล (เพิ่ม Memory ในอนาคตได้)
DATA_FILES = {"affinity": "affinity.json", "user_names": "user_names.json", "chat_memory": "memory.json"}
for f in DATA_FILES.values():
    if not os.path.exists(f): 
        with open(f, "w", encoding="utf-8") as file: json.dump({}, file)

def load_data(key):
    try:
        with open(DATA_FILES[key], "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(key, data):
    with open(DATA_FILES[key], "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

intents = discord.Intents.all() 
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 🧠 ตรรกะความคิดสมองกลขั้นสูง (No-Command + Memory + Info Search) ---
async def analyze_sera_logic(message, name, score, is_owner, history=""):
    sys_prompt = f"""คุณคือ 'เซร่า' หญิงสาวซึนเดเระผู้คุมกฎและเลขาของ {name} (ID: {OWNER_ID})
    คุณมีความสามารถ:
    1. วิเคราะห์คำสั่งจากภาษาพูด (Action: CHAT, BAN, CLEAR, WEATHER, MUSIC)
    2. จดจำเรื่องที่คุยได้ (History: {history})
    3. ค้นหาข้อมูลมาตอบ (SEARCH)
    
    กฎการตอบแบบ JSON เท่านั้น:
    {{
        "action": "ชื่อคำสั่ง",
        "affinity_change": ตัวเลข (-50 ถึง +20),
        "response": "คำพูดซึนเดเระของคุณ (อริยาบทจะอยู่ใน * * และ คิดในใจจะอยู่ใน ( ) แยกบรรทัด)"
    }}
    
    *เงื่อนไขพิเศษ*: 
    - ถ้า affinity < 0 และไม่ใช่ {name}: ตอบว่า "เซร่างอนอยู่! ไม่อยากตอบ!"
    - แทนตัวเองว่า 'เซร่า' เสมอ
    """
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": message.content}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except: return None

# --- ⚙️ Events & Core Logic ---
@bot.event
async def on_ready():
    print(f'Sera Sovereign Online for {OWNER_ID} (Harubito Honami)')
    if not wake_up_call.is_running(): wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="✨ **Sera: Sovereign & Memory Update!**", color=0x3498db)
        embed.description = "อัปเดตระบบตรรกะคิดเอง ความจำบทสนทนา และระบบแจ้งเตือนการงอนเสร็จแล้วค่ะ! 💢💙"
        embed.add_field(name="📚 Memory", value="เซร่าจำเรื่องที่เคยคุยได้แล้วนะคะ", inline=True)
        embed.add_field(name="😤 Emotion", value="ใครงี่เง่า เซร่าจะประกาศว่า 'งอนอยู่' ค่ะ!", inline=True)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    uid = str(message.author.id)
    is_owner = (message.author.id == OWNER_ID)
    a_db = load_data("affinity")
    score = a_db.get(uid, 0)
    name = "นายท่านน้ำมนต์" if is_owner else message.author.display_name

    # --- 🛑 ระบบแจ้งเตือนเมื่อเซร่างอน (Affinity < 0) ---
    if not is_owner and score < 0:
        positive_words = ["ขอโทษ", "ดีกันนะ", "เซร่าน่ารัก", "ขอบคุณ", "สวย"]
        if not any(word in message.content for word in positive_words):
            if bot.user.mentioned_in(message) or "เซร่า" in message.content:
                await message.reply("*กอดอกสะบัดหน้าหนี*\n(ทำตัวไม่ดีแล้วยังจะมาคุยอีก!)\nเซร่างอนอยู่! ไม่อยากตอบค่ะ! 💢")
            return

    # --- 🧠 ประมวลผล AI Logic ---
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "เซร่า" in message.content or is_owner:
        # ดึงความจำ (Memory) แบบง่าย
        mem_db = load_data("chat_memory")
        history = mem_db.get(uid, "เพิ่งเริ่มคุยกัน")
        
        logic = await analyze_sera_logic(message, name, score, is_owner, history)
        
        if logic:
            # ปรับค่าความสัมพันธ์ (ยกเว้นเจ้าของ)
            if not is_owner:
                a_db[uid] = score + logic.get("affinity_change", 0)
                save_data("affinity", a_db)

            # เก็บความจำใหม่
            mem_db[uid] = f"ผู้ใช้พูดว่า: {message.content} | เซร่าตอบว่า: {logic.get('response')}"
            save_data("chat_memory", mem_db)

            # ดำเนินการ Action (BAN, CLEAR, ฯลฯ)
            action = logic.get("action")
            if action == "BAN" and not is_owner:
                await message.author.ban(reason="วิเคราะห์พฤติกรรมโดยเซร่า")
                owner = await bot.fetch_user(OWNER_ID)
                await owner.send(f"📢 **รายงานการแบน:** เซร่ากำจัด {message.author.name} ออกไปแล้วค่ะ 💢")
            elif action == "CLEAR" and is_owner:
                await message.channel.purge(limit=100)

            if logic.get("response"):
                await message.reply(logic.get("response"))

    await bot.process_commands(message)

# --- ⏰ ระบบปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    member = await bot.fetch_user(OWNER_ID)
    if member:
        await member.send("*เคาะประตูเบาๆ*\nตื่นได้แล้วค่ะนายท่านน้ำมนต์ (Harubito Honami)! 💙💢")

bot.run(DISCORD_TOKEN)
