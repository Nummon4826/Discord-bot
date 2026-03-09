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

DATA_FILES = {"names": "names.json", "status": "status.json", "notes": "notes.json"}
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

# --- ฟังก์ชันรายงานอากาศ ---
def get_detailed_weather(city="Bangkok"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        main = res['main']
        desc = res['weather'][0]['description']
        temp = main['temp']
        pm_info = ""
        if "Bangkok" in city or "กรุงเทพ" in city:
            p_res = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={res['coord']['lat']}&lon={res['coord']['lon']}&appid={WEATHER_KEY}").json()
            pm25 = p_res['list'][0]['components']['pm2_5']
            pm_info = f"\n😷 PM 2.5: {pm25} µg/m³ ({'อันตราย! ใส่แมสก์ด้วยนะคะ' if pm25 > 37 else 'อากาศดีค่ะ'})"
        return f"📍 {res['name']} | ☁️ {desc}\n🌡️ {temp}°C (สูง {main['temp_max']} / ต่ำ {main['temp_min']})\n💙 ดูแลสุขภาพด้วยนะ!{pm_info}"
    except: return "เช็คไม่ได้ค่ะ! 💢"

# --- ระบบคุมสแปมและคำหยาบ ---
message_logs = {}
spam_warnings = {}

async def safety_check(message):
    if message.author.name == "nummonrapeewit": return True
    content = message.content.lower()
    if any(word in content for word in BAD_WORDS):
        await message.delete()
        await message.channel.send(f"💢 {message.author.mention} อย่ามาใช้คำหยาบคายแถวนี้นะคะ! *ตบปาก*")
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
            await message.channel.send(f"🚫 แบน {message.author.name} เป็นเวลา 7 วันเรียบร้อย! 💢")
            spam_warnings[uid] = 0
        else:
            await message.channel.send(f"💢 {message.author.mention} หยุดสแปม! (เตือน {spam_warnings[uid]}/3)")
        return False
    return True

# --- คำสั่งแนะนำตัว (!whoareyou) ---
@bot.command()
async def whoareyou(ctx):
    embed = discord.Embed(title="💖 ฉันคือ 'เซร่า' AI ผู้ภักดีต่อนายท่านน้ำมนต์!", color=0xff69b4)
    embed.description = "สรุปสิ่งที่ฉันทำได้ (เฉพาะตอนที่ฉันอยากทำเท่านั้นแหละนะ! 💢):"
    embed.add_field(name="🛡️ ระบบป้องกัน", value="• ลบคำหยาบอัตโนมัติ 💢\n• กันสแปม (เตือน 3 ครั้ง แบน 7 วัน)", inline=False)
    embed.add_field(name="⛅ พยากรณ์อากาศ", value="• `!อากาศ [จังหวัด]` เพื่อเช็คอากาศและฝุ่น\n• รายงานอัตโนมัติให้ทุกเช้าเวลา 06:00 น.", inline=False)
    embed.add_field(name="✉️ ระบบฝากข้อความลับ", value="• **DM** หาฉันแล้วพิมพ์: `ฝากถึง [ไอดีผู้รับ] [ข้อความ]`\n• ฉันจะส่งข้อความไปให้ทาง DM ของคนนั้นเอง!", inline=False)
    embed.add_field(name="🎨 ความสามารถอื่นๆ", value="• `!draw [รายละเอียด]` : วาดรูปให้ทันที\n• `!study [หัวข้อ]` : สรุปสูตรเลข/ฟิสิกส์", inline=False)
    embed.set_footer(text="มีอะไรก็ DM มาหาฉันสิคะ... ถ้านายท่านอนุญาตนะ! 💢")
    await ctx.reply(embed=embed)

@bot.command(name="อากาศ")
async def weather_cmd(ctx, *, province="Bangkok"):
    await ctx.reply(get_detailed_weather(province))

@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{prompt.replace(' ', '_')}?width=1024&height=1024&seed={time.time()}"
    await ctx.reply(embed=discord.Embed(title="วาดให้แล้วค่ะ! 🎨").set_image(url=url))

@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def morning_job():
    CHANNEL_ID = 123456789012345678 # <<< เปลี่ยนเป็น ID ห้องของนายท่าน
    channel = bot.get_channel(CHANNEL_ID)
    if channel: await channel.send(f"ตื่นค่ะ นายท่านน้ำมนต์! อากาศวันนี้:\n{get_detailed_weather('Bangkok')}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not morning_job.is_running(): morning_job.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # --- 1. ระบบจัดการผ่าน DM ---
    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()
        
        # ก) นายท่านส่งสถานะ (บอกว่าไปไหน)
        if message.author.name == "nummonrapeewit" and not content.startswith("ฝากถึง"):
            status_db = load_data("status")
            status_db["current"] = content
            save_data("status", status_db)
            await message.reply(f"รับทราบค่ะนายท่าน! เซร่าจะบอกทุกคนว่านายท่านกำลัง '{content}' อยู่ค่ะ 💙")
            return

        # ข) ระบบฝากข้อความลับ (ฝากถึง [ไอดี] [ข้อความ])
        if content.startswith("ฝากถึง"):
            try:
                parts = content.split(" ", 2)
                target_id = parts[1]
                msg_to_send = parts[2]
                notes = load_data("notes")
                if target_id not in notes: notes[target_id] = []
                notes[target_id].append({"msg": msg_to_send, "time": str(datetime.datetime.now(TIMEZONE))})
                save_data("notes", notes)
                await message.reply("💢 รับเรื่องไว้แล้วค่ะ! จะส่งให้ทาง DM ของคนนั้นเมื่อเขาโผล่มานะคะ!")
                return
            except:
                await message.reply("💢 พิมพ์ผิดค่ะ! ต้องพิมพ์ว่า: `ฝากถึง [ไอดีคนรับ] [ข้อความ]`")
                return

    # --- 2. Safety Check (Server Only) ---
    if not isinstance(message.channel, discord.DMChannel):
        if not await safety_check(message): return

    await bot.process_commands(message)

    # --- 3. ตรวจสอบข้อความฝาก (ส่งทาง DM) ---
    notes = load_data("notes")
    uid = str(message.author.id)
    if uid in notes and notes[uid]:
        try:
            for n in notes[uid]:
                dm_channel = await message.author.create_dm()
                await dm_channel.send(f"🔔 มีข้อความฝากถึงคุณค่ะ: '{n['msg']}'\n*(ฉันส่งให้ตามหน้าที่เท่านั้นแหละนะ! 💢)*")
            notes[uid] = []
            save_data("notes", notes)
        except: pass

    # --- 4. AI Chat (Groq) ---
    if bot.user.mentioned_in(message) or (isinstance(message.channel, discord.DMChannel) and not message.content.startswith("ฝากถึง")):
        is_owner = (message.author.name == "nummonrapeewit")
        u_input = message.content.replace(f'<@{bot.user.id}>', '').strip()
        status_db = load_data("status")
        current_status = status_db.get("current", "ไม่ทราบว่าไปไหน")
        
        system_rules = f"คุณคือ 'เซร่า' สาวซึนเดเระผู้ภักดีต่อนายท่านน้ำมนต์ (nummonrapeewit) ถ้านายท่านไม่อยู่บอกว่าไป '{current_status}' เรียกนายท่านว่า 'นายท่านน้ำมนต์' คนอื่นเรียก 'คุณ' ตอบด้วยอริยาบท * * และอีโมจิ 💢"
        
        try:
            chat_comp = client.chat.completions.create(
                messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": u_input}],
                model="llama-3.3-70b-versatile"
            )
            await message.reply(chat_comp.choices[0].message.content)
        except: await message.reply("ระบบรวนค่ะ! 💢")

bot.run(DISCORD_TOKEN)
