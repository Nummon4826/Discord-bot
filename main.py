import discord
import os
import datetime
import pytz
import requests
import json
import asyncio
from groq import Groq
from discord.ext import commands, tasks

# --- 🔒 ข้อมูลความปลอดภัย (ผู้สร้าง: นายท่านน้ำมนต์) ---
OWNER_ID = 841691286125019186 
LOG_CHANNEL_ID = 1299667544814391349
MUSIC_PATH = "./music"

if not os.path.exists(MUSIC_PATH):
    os.makedirs(MUSIC_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบฐานข้อมูล
DATA_FILES = {"affinity": "affinity.json", "user_names": "user_names.json"}
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

# --- 🌡️ รายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิ {temp}°C ค่ะ (ดูแลสุขภาพด้วยนะคะ!)"
    except: return "เช็คอากาศไม่ได้ แต่เซร่ามาปลุกนายท่านแล้วนะคะ 💢"

# --- ⏰ ระบบปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    report = get_morning_report()
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูห้องเบาๆ*\n(ตื่นมาคุยกับเซร่าได้แล้วค่ะ...)\nอรุณสวัสดิ์ค่ะนายท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}\n\nเซร่ารออยู่นะคะ! 💙💢")
        except: pass

# --- 🧠 ตรรกะความคิดสมองกล (No-Command Logic) ---
async def analyze_sera_logic(message, name, is_owner):
    sys_prompt = f"""คุณคือ 'เซร่า' สาวซึนเดเระผู้คุมกฎเซิร์ฟเวอร์ของ {name} (ผู้สร้าง)
    วิเคราะห์ข้อความและตอบเป็น JSON เท่านั้น:
    {{
        "action": "CHAT", "BAN", "CLEAR", "WEATHER", หรือ "MUSIC",
        "affinity_change": ตัวเลข (-50 ถึง +20),
        "response": "คำพูดซึนเดเระของคุณ"
    }}
    กฎ:
    - แทนตัวเองว่า 'เซร่า'
    - อริยาบทใน * * และคิดในใจใน ( ) แยกบรรทัดเสมอ
    - ถ้าหยาบคาย: affinity_change ติดลบหนักๆ
    - ถ้าเป็น {name}: ให้คลั่งรักแต่ซึนเดเระ ใช้อีโมจิ 💢
    """
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": message.content}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except: return None

# --- ⚙️ Events & Autonomous Logic ---
@bot.event
async def on_ready():
    print(f'Sera Sovereign Online for {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="✨ **Sera: Sovereign Update Complete!**", color=0x3498db)
        embed.description = "อัปเดตระบบตรรกะคิดเองและผู้คุมกฎเสร็จสมบูรณ์แล้วค่ะ! 💢💙\n\n**ฟังก์ชันใหม่:**\n- 🧠 คิดเองผ่านภาษาพูด (No-Command)\n- 🛡️ แบนคนป่วน/หยาบคายอัตโนมัติ\n- 💖 ระบบงอน/ง้อ (ติดลบ = เมิน)\n- 📩 รายงานลับเข้า DM นายท่าน"
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    uid = str(message.author.id)
    is_owner = (message.author.id == OWNER_ID)
    a_db = load_data("affinity")
    n_db = load_data("user_names")
    
    score = a_db.get(uid, 0)
    name = "นายท่านน้ำมนต์" if is_owner else n_db.get(uid, message.author.display_name)

    # --- 🛑 ระบบงอน (ติดลบเมิน ยกเว้นง้อ) ---
    if not is_owner and score < 0:
        if not any(word in message.content for word in ["ขอโทษ", "ดีกันนะ", "เซร่าน่ารัก"]):
            return

    # --- 🧠 ประมวลผลตรรกะ AI ---
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "เซร่า" in message.content or is_owner:
        logic = await analyze_sera_logic(message, name, is_owner)
        if logic:
            if not is_owner:
                a_db[uid] = score + logic.get("affinity_change", 0)
                save_data("affinity", a_db)

            action = logic.get("action")
            if action == "BAN" and not is_owner:
                try:
                    await message.author.ban(reason="พฤติกรรมไม่เหมาะสม (วิเคราะห์โดยเซร่า)")
                    owner = await bot.fetch_user(OWNER_ID)
                    await owner.send(f"📢 **รายงานการแบน:** เซร่าแบน {message.author.name} ออกไปแล้วค่ะ! 💢")
                except: pass
            elif action == "CLEAR" and is_owner:
                await message.channel.purge(limit=100)
                await message.send("*กวาดแชทให้สะอาดค่ะ* 🧹", delete_after=3)

            if logic.get("response"):
                await message.reply(logic.get("response"))

    await bot.process_commands(message)

# --- 📜 Commands พื้นฐาน ---
@bot.command()
async def weather(ctx):
    report = get_morning_report()
    await ctx.reply(f"*เช็คหน้าจอ*\n{report} 💢")

@bot.command()
async def relationship(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.reply("*หน้าแดง*\nนายท่านน้ำมนต์คือที่สุดของเซร่าค่ะ! 💙💢")
    else:
        db = load_data("affinity")
        s = db.get(str(ctx.author.id), 0)
        await ctx.reply(f"คะแนนของคุณคือ {s} ค่ะ 💢")

bot.run(DISCORD_TOKEN)
