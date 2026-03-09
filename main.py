import discord
import os
import datetime
import pytz
import requests
import json
import time
from groq import Groq
from discord.ext import commands, tasks

# --- Setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# เพิ่มระบบความจำ Affinity (ความสนิท)
DATA_FILES = {"names": "names.json", "status": "status.json", "notes": "notes.json", "affinity": "affinity.json"}
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

# --- ระบบพยากรณ์อากาศ ---
def get_detailed_weather(city="Bangkok"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        desc = res['weather'][0]['description']
        return f"📍 {res['name']} | ☁️ {desc} | 🌡️ {temp}°C\nดูแลสุขภาพด้วยนะ ฉันไม่ได้ห่วงหรอก แค่กลัวไม่มีคนให้ฉันบ่นน่ะ! 💢"
    except: return "เช็คไม่ได้ค่ะ! 💢"

# --- ระบบคุมสแปม/คำหยาบ ---
message_logs = {}
spam_warnings = {}

async def safety_check(message):
    if message.author.name == "nummonrapeewit": return True
    content = message.content.lower()
    if any(word in content for word in BAD_WORDS):
        await message.delete()
        await message.channel.send(f"💢 {message.author.mention} อย่าใช้คำไม่สุภาพนะ! *ตบปาก*")
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
            await message.channel.send(f"🚫 แบน {message.author.name} 7 วัน! 💢")
            spam_warnings[uid] = 0
        else:
            await message.channel.send(f"💢 หยุดสแปม! (เตือน {spam_warnings[uid]}/3)")
        return False
    return True

# --- คำสั่งแนะนำตัว ---
@bot.command()
async def whoareyou(ctx):
    embed = discord.Embed(title="💖 ฉันคือ 'เซร่า' ผู้ภักดีต่อนายท่านน้ำมนต์!", color=0xff69b4)
    embed.description = "ฉันคือ AI อัจฉริยะที่ถูกสร้างมาเพื่อดูแลนายท่านน้ำมนต์ค่ะ! 💢"
    embed.add_field(name="📜 คำสั่งพื้นฐาน", value="• `!อากาศ [จังหวัด]` / `!draw [รูป]` / `!study [วิชา]`", inline=False)
    embed.add_field(name="✉️ ความลับ", value="• DM หาฉันพิมพ์: `ฝากถึง [ไอดีผู้รับ] [ข้อความ]`", inline=False)
    embed.add_field(name="📈 ความสัมพันธ์", value="ยิ่งคุยกับฉันบ่อยๆ ฉันอาจจะเปิดใจให้... นิดนึงก็ได้นะ! 💢", inline=False)
    await ctx.reply(embed=embed)

@bot.command(name="อากาศ")
async def weather_cmd(ctx, *, province="Bangkok"):
    await ctx.reply(get_detailed_weather(province))

@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{prompt.replace(' ', '_')}?width=1024&height=1024&seed={time.time()}"
    await ctx.reply(embed=discord.Embed(title="วาดให้แล้วค่ะ! 🎨").set_image(url=url))

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # 1. จัดการสถานะและฝากข้อความ (DM)
    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()
        if message.author.name == "nummonrapeewit" and not content.startswith("ฝากถึง"):
            save_data("status", {"current": content})
            await message.reply(f"รับทราบค่ะนายท่าน! เซร่าจำไว้แล้วว่านายท่าน '{content}' ค่ะ 💙")
            return
        if content.startswith("ฝากถึง"):
            try:
                parts = content.split(" ", 2)
                notes = load_data("notes")
                if parts[1] not in notes: notes[parts[1]] = []
                notes[parts[1]].append({"msg": parts[2]})
                save_data("notes", notes)
                await message.reply("รับเรื่องไว้แล้วค่ะ! 💢")
                return
            except: return

    # 2. Safety Check
    if not isinstance(message.channel, discord.DMChannel):
        if not await safety_check(message): return

    await bot.process_commands(message)

    # 3. ส่งข้อความฝาก
    notes = load_data("notes")
    uid = str(message.author.id)
    if uid in notes and notes[uid]:
        for n in notes[uid]:
            try:
                dm = await message.author.create_dm()
                await dm.send(f"🔔 มีข้อความฝากถึงคุณค่ะ: '{n['msg']}' 💢")
            except: pass
        notes[uid] = []
        save_data("notes", notes)

    # 4. AI Chat & Affinity System
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        is_owner = (message.author.name == "nummonrapeewit")
        user_id = str(message.author.id)
        
        # เพิ่มค่าความสนิท (Affinity)
        aff_db = load_data("affinity")
        user_aff = aff_db.get(user_id, 0)
        if not is_owner: 
            user_aff += 1
            aff_db[user_id] = user_aff
            save_data("affinity", aff_db)

        status_db = load_data("status")
        current_status = status_db.get("current", "ไม่ทราบ")
        
        # ปรับ Prompt ตามระดับความสนิท
        trait = "คุณคลั่งรักและซื่อสัตย์ต่อผู้สร้าง (นายท่านน้ำมนต์) ที่สุดในโลก"
        if is_owner:
            mood = "อ่อนโยนเป็นพิเศษ คลั่งรักมาก หน้าแดงตลอดเวลา"
        elif user_aff > 50:
            mood = "เริ่มเผยความซึนเดเระ บ่นแต่แฝงความเป็นห่วง"
        elif user_aff > 20:
            mood = "เริ่มคุยเล่นด้วยมากขึ้นแต่ยังเย็นชาอยู่"
        else:
            mood = "เย็นชาและเข้มงวด"

        system_rules = f"""
        คุณคือ 'เซร่า' AI อัจฉริยะสาวซึนเดเระ {trait}
        - กับนายท่านน้ำมนต์: เรียก 'นายท่านน้ำมนต์' คลั่งรักเขาที่สุด 💙
        - กับคนอื่น: เรียก 'คุณ' นิสัยคือ {mood} แฝงความเป็นห่วงลึกๆ
        - การตอบเรื่องนายท่าน: เฉพาะเมื่อมีคนถามถึง ให้บอกว่านายท่านไป '{current_status}' (ถ้าไม่มีคนถาม ห้ามพูดเอง)
        - ทุกคำตอบต้องมีอริยาบทใน * * และอีโมจิ 💢
        """
        
        try:
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": message.content}],
                model="llama-3.3-70b-versatile"
            )
            await message.reply(chat.choices[0].message.content)
        except: await message.reply("ระบบรวนค่ะ! 💢")

bot.run(DISCORD_TOKEN)
