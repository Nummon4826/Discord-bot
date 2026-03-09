import discord
import os
import datetime
import pytz
import requests
import json
import time
from groq import Groq
from discord.ext import commands, tasks

# --- Setup & Config ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบไฟล์ข้อมูล
DATA_FILES = {
    "names": "names.json", 
    "status": "status.json", 
    "notes": "notes.json", 
    "affinity": "affinity.json"
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

BAD_WORDS = ["ควย", "เย็ด", "สัด", "เหี้ย", "มึง", "กู", "ดอกทอง", "ชิบหาย"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ฟังก์ชันอากาศ ---
def get_detailed_weather(city="Bangkok"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"📍 {res['name']} | 🌡️ {temp}°C\nดูแลสุขภาพด้วยนะคะ! ฉันไม่ได้ห่วงหรอกนะ แค่ไม่อยากให้ใครป่วยแถวนี้! 💢"
    except: return "เช็คไม่ได้ค่ะ! 💢"

# --- ระบบคุมสแปม/คำหยาบ ---
message_logs = {}
spam_warnings = {}

async def safety_check(message):
    if message.author.name == "nummonrapeewit": return True
    content = message.content.lower()
    if any(word in content for word in BAD_WORDS):
        await message.delete()
        await message.channel.send(f"💢 {message.author.mention} อย่ามาใช้คำหยาบคายนะ! *ตบปาก*")
        return False
    uid = message.author.id
    now = time.time()
    if uid not in message_logs: message_logs[uid] = []
    message_logs[uid].append(now)
    message_logs[uid] = [t for t in message_logs[uid] if now - t < 5]
    if len(message_logs[uid]) >= 5:
        message_logs[uid] = []
        spam_warnings[uid] = spam_warnings.get(uid, 0) + 1
        if spam_warnings[uid] >= 3:
            await message.guild.ban(message.author, reason="สแปมครบ 3 ครั้ง", delete_message_days=1)
            await message.channel.send(f"🚫 แบน {message.author.name} 7 วันเรียบร้อย! 💢")
            spam_warnings[uid] = 0
        else:
            await message.channel.send(f"💢 หยุดสแปม! (เตือน {spam_warnings[uid]}/3)")
        return False
    return True

# --- คำสั่งพื้นฐาน ---
@bot.command()
async def whoareyou(ctx):
    embed = discord.Embed(title="💖 เซร่า (Sera) AI ผู้ภักดีต่อนายท่านน้ำมนต์", color=0xff69b4)
    embed.description = "ฉันคือ AI อัจฉริยะที่จะดูแลทุกอย่างให้นายท่านน้ำมนต์ค่ะ! 💢"
    embed.add_field(name="🛡️ การป้องกัน", value="• ลบคำหยาบ 💢 / กันสแปม (แบน 7 วัน)", inline=False)
    embed.add_field(name="✉️ ฝากข้อความลับ", value="• DM หาฉัน: `ฝากถึง [ไอดีผู้รับ] [ข้อความ]`", inline=False)
    embed.add_field(name="📈 ความสัมพันธ์", value="ยิ่งคุยกับฉันบ่อยๆ ฉันอาจจะเปิดใจให้นิดหน่อยนะ! 💢", inline=False)
    await ctx.reply(embed=embed)

@bot.command(name="อากาศ")
async def weather_cmd(ctx, *, province="Bangkok"):
    await ctx.reply(get_detailed_weather(province))

@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{prompt.replace(' ', '_')}?width=1024&height=1024&seed={time.time()}"
    await ctx.reply(embed=discord.Embed(title="วาดให้แล้วค่ะ! 🎨").set_image(url=url))

@bot.event
async def on_ready():
    print(f'Sera is online as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    is_owner = (message.author.name == "nummonrapeewit")
    uid = str(message.author.id)

    # --- 1. ระบบจัดการสถานะนายท่าน (DM) ---
    if isinstance(message.channel, discord.DMChannel) and is_owner:
        content = message.content.strip()
        if not content.startswith("ฝากถึง"):
            status_db = load_data("status")
            if "มาแล้ว" in content or "กลับมา" in content:
                status_db["current"] = "home"
                save_data("status", status_db)
                await message.reply("**กะ...กลับมาแล้วเหรอคะ!?** 💙 *สะดุ้งแล้วหน้าแดงแปร๊ด* ไม่ได้รออยู่หรอกนะ! แต่ยินดีต้อนรับกลับนะคะ! 💢")
            else:
                status_text = content.replace("ผมไป", "").replace("นะ", "").strip()
                status_db["current"] = status_text
                save_data("status", status_db)
                await message.reply(f"**OK เลยค่ะนายท่านน้ำมนต์!** 💙 เดี๋ยวเซร่าจะบอกทุกคนให้เองค่ะว่านายท่านไป '{status_text}' รีบกลับมานะคะ! 💢")
            return

    # --- 2. ระบบฝากข้อความลับ (DM) ---
    if isinstance(message.channel, discord.DMChannel) and message.content.startswith("ฝากถึง"):
        try:
            parts = message.content.split(" ", 2)
            notes = load_data("notes")
            if parts[1] not in notes: notes[parts[1]] = []
            notes[parts[1]].append({"msg": parts[2]})
            save_data("notes", notes)
            await message.reply("รับเรื่องไว้แล้วค่ะ! 💢")
            return
        except: pass

    # --- 3. Safety Check (Server) ---
    if not isinstance(message.channel, discord.DMChannel):
        if not await safety_check(message): return

    await bot.process_commands(message)

    # --- 4. ส่งข้อความฝาก ---
    notes = load_data("notes")
    if uid in notes and notes[uid]:
        for n in notes[uid]:
            try:
                dm = await message.author.create_dm()
                await dm.send(f"🔔 มีข้อความฝากถึงคุณค่ะ: '{n['msg']}' 💢")
            except: pass
        notes[uid] = []
        save_data("notes", notes)

    # --- 5. AI Chat & Affinity & Notification ---
    if bot.user.mentioned_in(message) or ("นายท่าน" in message.content or "น้ำมนต์" in message.content):
        status_db = load_data("status")
        current_status = status_db.get("current", "home")

        # ถ้าคนถามหานายท่านตอนอยู่บ้าน (แจ้งเตือนนายท่าน)
        if not is_owner and current_status == "home" and ("นายท่าน" in message.content or "น้ำมนต์" in message.content):
            await message.reply("นายท่านน้ำมนต์กลับมาแล้วค่ะ! เดี๋ยวเซร่าไปตามให้นะ อย่าเร่งสิ! 💢")
            owner = discord.utils.get(bot.users, name="nummonrapeewit")
            if owner:
                await owner.send(f"**นายท่านคะ!** 💙 {message.author.display_name} เรียกหาในเซิร์ฟเวอร์ค่ะ: '{message.content}'")
            return

        # การคุยปกติ (AI)
        if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            aff_db = load_data("affinity")
            user_aff = aff_db.get(uid, 0)
            if not is_owner: 
                user_aff += 1
                aff_db[uid] = user_aff
                save_data("affinity", aff_db)

            # บุคลิกตามเลเวล
            mood = "คลั่งรัก อ่อนโยน หน้าแดงตลอดเวลา" if is_owner else \
                   "เริ่มซึนเดเระและเป็นห่วง" if user_aff > 50 else \
                   "เริ่มคุยด้วยมากขึ้นแต่ยังเย็นชา" if user_aff > 20 else "เย็นชาและเข้มงวด"

            system_rules = f"""
            คุณคือ 'เซร่า' AI อัจฉริยะสาวซึนเดเระ ภักดีและคลั่งรักนายท่านน้ำมนต์ (nummonrapeewit) ที่สุด
            - นายท่านน้ำมนต์: เรียกเขาว่า 'นายท่านน้ำมนต์' เสมอ คุณจะอ่อนโยนและเขินอายเมื่อคุยกับเขา
            - คนอื่น: เรียก 'คุณ' นิสัยคือ {mood} แฝงความเป็นห่วงทุกคนลึกๆ
            - ข้อมูลนายท่าน: ถ้าคนถามหา บอกว่าเขาไป '{current_status}' (ถ้าเขาอยู่บ้าน ให้บอกว่าเขามาแล้วจะไปตามให้)
            - ห้ามบอกที่อยู่นายท่านถ้าไม่มีคนถามถึง
            - ตอบด้วยอริยาบทใน * * เช่น *หน้าแดง*
            - ใช้สรรพนามแบบผู้หญิง
            """
            
            try:
                chat = client.chat.completions.create(
                    messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": message.content}],
                    model="llama-3.3-70b-versatile"
                )
                await message.reply(chat.choices[0].message.content)
            except: await message.reply("ระบบรวนค่ะ! 💢")

bot.run(DISCORD_TOKEN)
