import discord
import os
import datetime
import pytz
import requests
import json
import time
from groq import Groq
from discord.ext import commands, tasks

# --- 🔒 ข้อมูลความปลอดภัยและตั้งค่า ---
OWNER_ID = 841691286125019186 
LOG_CHANNEL_ID = 1299667544814391349 # ช่องสำหรับรายงานตัวเมื่ออัปเดตเสร็จ

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบไฟล์ข้อมูล
DATA_FILES = {
    "status": "status.json", 
    "notes": "notes.json", 
    "affinity": "affinity.json", 
    "user_names": "user_names.json"
}

for f in DATA_FILES.values():
    if not os.path.exists(f): 
        with open(f, "w", encoding="utf-8") as file: json.dump({}, file)

def load_data(key):
    try:
        with open(DATA_FILES[key], "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(key, data):
    with open(DATA_FILES[key], "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ฟังก์ชันวิเคราะห์อารมณ์คำพูด (Sentiment Analysis แบบง่าย) ---
def analyze_sentiment(text):
    positive = ["ขอบคุณ", "น่ารัก", "เก่ง", "ดีมาก", "สวย", "ชอบ", "ใจดี", "หิวไหม", "เหนื่อยไหม"]
    negative = ["นิสัยไม่ดี", "โง่", "น่ารำคาญ", "เกลียด", "หุบปาก", "บ้า", "กวน", "ไม่ชอบ"]
    score = 0
    for word in positive:
        if word in text: score += 10
    for word in negative:
        if word in text: score -= 15
    return score

# --- ฟังก์ชันรายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิตอนนี้ {temp}°C ค่ะ"
    except: return "เช็คอากาศไม่ได้ แต่เซร่าอยู่ตรงนี้แล้วค่ะ 💢"

# --- คำสั่งสำหรับคนทั่วไป ---
@bot.command()
async def weather(ctx):
    """เช็คพยากรณ์อากาศ"""
    report = get_morning_report()
    await ctx.reply(f"*หยิบหน้าจอพยากรณ์อากาศขึ้นมาดู*\n\n{report} นะคะ 💢")

@bot.command()
async def myname(ctx, *, name: str):
    """ให้เซร่าจำชื่อเล่น"""
    db = load_data("user_names")
    db[str(ctx.author.id)] = name
    save_data("user_names", db)
    await ctx.reply(f"*จดบันทึกลงสมุดส่วนตัว*\n\nเซร่าจำชื่อคุณ '{name}' ไว้ในระบบ ID เรียบร้อยแล้วค่ะ อย่าลืมตัวบ่อยนะคะ 💢")

@bot.command()
async def relationship(ctx):
    """เช็คค่าความสัมพันธ์"""
    if ctx.author.id == OWNER_ID:
        await ctx.reply("*หน้าแดงจัดจนตัวสั่น*\n\nสำหรับท่านน้ำมนต์... สถานะคือ 'คลั่งรักที่สุดในโลก' ค่ะ! 💙💢")
        return
    
    aff_db = load_data("affinity")
    score = aff_db.get(str(ctx.author.id), 0)
    
    status = "แย่"
    if score >= 100: status = "ดีเยี่ยม"
    elif score >= 50: status = "ดี"
    elif score >= 0: status = "เฉย"
    
    await ctx.reply(f"*ปัดฝุ่นที่เสื้อ*\n\nค่าความสัมพันธ์ของคุณอยู่ในระดับ: '{status}' ค่ะ (คะแนน: {score}) 💢")

# --- คำสั่งสำหรับท่านน้ำมนต์ (Owner Only) ---
@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดมือเบาๆ*\n\nทำความสะอาดให้ท่านน้ำมนต์เรียบร้อยแล้วค่ะ 🧹✨", delete_after=5)

@bot.command()
async def test(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.reply("*ตรวจสอบแผงวงจร*\n\nระบบทุกอย่างปกติพร้อมรับใช้ท่านน้ำมนต์ค่ะ 💙")

# --- ระบบแจ้งเตือนเมื่ออัปเดตเสร็จ ---
@bot.event
async def on_ready():
    print(f'Sera Emotional System Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="*ย่อตัวคำนับอย่างสง่างาม*", color=0x3498db)
        embed.description = "เซร่าอัปเดตระบบ 'หัวใจดิจิทัล' และสรรพนามกุลสตรีเสร็จสิ้นแล้วค่ะ!\n\n**รายการคำสั่งที่คนทั่วไปใช้งานได้:**"
        embed.add_field(name="🌡️ !weather", value="เช็คสภาพอากาศปัจจุบัน", inline=True)
        embed.add_field(name="📝 !myname [ชื่อ]", value="ให้เซร่าจดจำชื่อเล่นของคุณ (ผูกกับ ID)", inline=True)
        embed.add_field(name="💖 !relationship", value="เช็คระดับความสัมพันธ์กับเซร่า", inline=True)
        embed.set_footer(text="ปล. คำสั่งลับของท่านน้ำมนต์ เซร่าจะเก็บเป็นความลับสูงสุดค่ะ 💢")
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    # --- ระบบสะสมค่าความสัมพันธ์ (สำหรับคนอื่น) ---
    if not is_owner:
        aff_db = load_data("affinity")
        score_change = analyze_sentiment(message.content)
        if score_change != 0:
            current_score = aff_db.get(uid, 0)
            aff_db[uid] = current_score + score_change
            save_data("affinity", aff_db)

    # --- ระบบตอบโต้ AI ---
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        s_db, a_db, n_db = load_data("status"), load_data("affinity"), load_data("user_names")
        name = n_db.get(uid, message.author.display_name)
        score = a_db.get(uid, 0)

        # กำหนดระดับความซึนตามคะแนน
        if is_owner:
            mood = "คลั่งรักที่สุด หน้าแดงจัด อ่อนโยนและขี้อาย"
        elif score >= 100:
            mood = "ดีเยี่ยม: เริ่มมีความซึนเดเระแบบเห็นชัด เป็นห่วงแต่ปากแข็ง"
        elif score >= 50:
            mood = "ดี: สุภาพขึ้นแต่ยังรักษาระยะห่าง"
        elif score >= 0:
            mood = "เฉย: เย็นชาและทำตามหน้าที่เท่านั้น"
        else:
            mood = "แย่: รังเกียจและใช้คำพูดจิกกัด"

        sys_rules = f"""
        คุณคือ 'เซร่า' หญิงสาวกุลสตรีซึนเดเระ ภักดีต่อท่านน้ำมนต์ (ID: {OWNER_ID})
        - อริยาบทแยกบรรทัดกับประโยคพูดเสมอ
        - ท่านน้ำมนต์: คลั่งรัก (พิเศษคนเดียว)
        - {name}: {mood}
        - ใช้อีโมจิ 💢 สื่อถึงความซึน
        """
        try:
            chat = client.chat.completions.create(messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], model="llama-3.3-70b-versatile")
            await message.reply(chat.choices[0].message.content)
        except: pass

    await bot.process_commands(message)

# --- (Loop ปลุก 06:00 น. เหมือนโค้ดที่แล้ว) ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try: await member.send("*เคาะประตูเบาๆ*\n\nได้เวลาตื่นแล้วนะคะท่านน้ำมนต์ 💙💢")
        except: pass

bot.run(DISCORD_TOKEN)
