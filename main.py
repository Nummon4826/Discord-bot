import discord
import os
import datetime
import pytz
import requests
import json
import time
import asyncio
from groq import Groq
from discord.ext import commands, tasks

# --- 🔒 ข้อมูลความปลอดภัย (ID ของท่านน้ำมนต์) ---
OWNER_ID = 841691286125019186 
LOG_CHANNEL_ID = 1299667544814391349
MUSIC_PATH = "./music"

if not os.path.exists(MUSIC_PATH):
    os.makedirs(MUSIC_PATH)

# Setup API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบไฟล์ข้อมูล
DATA_FILES = {"status": "status.json", "affinity": "affinity.json", "user_names": "user_names.json"}
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
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 📅 ตารางสอบปี 2569 ---
SPECIAL_DATES = {
    "20260314": "*กุมมือท่านเบาๆ*\n\nวันนี้สอบ A-Level วันแรก สู้ๆ นะคะท่านน้ำมนต์ เซร่าเชียร์อยู่ค่ะ! 💙",
    "20260315": "*ส่งยิ้มให้กำลังใจ*\n\nA-Level วันที่สองแล้ว พักผ่อนให้เพียงพอด้วยนะคะ 💢",
    "20260316": "*รอรับที่หน้าประตู*\n\nวันสุดท้ายของ A-Level แล้วนะคะ! ทำให้เต็มที่เลยค่ะท่านน้ำมนต์ 💙",
    "20260321": "*ช่วยจัดเนคไทให้*\n\nวันนี้สอบตรงพระนครเหนือนะคะ ต้องไปให้ทัน 07:00 น. เดินทางปลอดภัยค่ะ! ⚙️"
}

# --- 🌡️ ฟังก์ชันรายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิในกทม. ตอนนี้ {temp}°C ค่ะ"
    except: return "เช็คอากาศไม่ได้ แต่เซร่ามาปลุกท่านแล้วนะคะ 💢"

# --- 🎵 ระบบเพลง (Music System) ---
class MusicButtons(discord.ui.View):
    def __init__(self, songs):
        super().__init__(timeout=60)
        for i, song in enumerate(songs[:25]):
            btn = discord.ui.Button(label=f"{i+1}. {song[:20]}", style=discord.ButtonStyle.primary, custom_id=song)
            btn.callback = self.play_callback
            self.add_item(btn)

    async def play_callback(self, interaction: discord.Interaction):
        song_name = interaction.data['custom_id']
        voice = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice and voice.is_connected():
            if voice.is_playing(): voice.stop()
            source = discord.FFmpegPCMAudio(os.path.join(MUSIC_PATH, song_name))
            voice.play(source)
            await interaction.response.send_message(f"*เริ่มบรรเลงเพลง {song_name} ให้ท่านฟังแล้วค่ะ* 🎵💢", ephemeral=True)
        else:
            await interaction.response.send_message("เซร่ายังไม่ได้เข้าสายสนทนาเลยนะคะ! 💢", ephemeral=True)

# --- ⏰ [FIXED] Loop ปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    now_str = datetime.datetime.now(TIMEZONE).strftime("%Y%m%d")
    report = get_morning_report()
    special = f"\n\n{SPECIAL_DATES.get(now_str, '')}" if now_str in SPECIAL_DATES else ""
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูห้องเบาๆ*\n\nอรุณสวัสดิ์ค่ะท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}{special}\n\nเซร่ารออยู่นะคะ 💙💢")
        except: pass

# --- 🛡️ ระบบกันสแปม ---
user_last_msg_time = {}
user_spam_count = {}

async def anti_spam_check(message):
    if message.author.id == OWNER_ID: return True
    uid = message.author.id
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 1.0:
        user_spam_count[uid] = user_spam_count.get(uid, 0) + 1
        if user_spam_count[uid] >= 5:
            try:
                await message.guild.ban(message.author, reason="Spamming", delete_message_days=1)
                await message.author.send("*ถอนหายใจ*\n\nเซร่าเตือนแล้วนะคะ กรุณาออกไปสงบสติอารมณ์ 7 วันค่ะ! 💢")
            except: pass
            return False
        return False
    user_last_msg_time[uid] = now
    user_spam_count[uid] = 0
    return True

# --- 🎭 ระบบตอบโต้ AI (คืนหัวใจให้เซร่า) ---
async def sera_ai_response(message, is_owner, uid):
    a_db, n_db = load_data("affinity"), load_data("user_names")
    name = n_db.get(uid, message.author.display_name)
    score = a_db.get(uid, 0)

    mood = "คลั่งรักท่านน้ำมนต์ที่สุด หน้าแดงจัด อ่อนโยนและขี้อาย" if is_owner else \
           "ซึนเดเระ: เป็นห่วงแต่ปากแข็ง" if score >= 100 else \
           "สุภาพแต่รักษาระยะห่าง" if score >= 50 else "เย็นชา"
    
    sys_rules = f"""
    คุณคือ 'เซร่า' หญิงสาวกุลสตรีซึนเดเระ ภักดีต่อท่านน้ำมนต์ (ID: {OWNER_ID})
    - อริยาบทแยกบรรทัดกับประโยคพูดเสมอ
    - ท่านน้ำมนต์: คลั่งรักเป็นพิเศษ
    - คู่สนทนาชื่อ {name}: สถานะคือ {mood}
    - พูดจาสุภาพ (ค่ะ/นะคะ) และใช้อีโมจิ 💢
    """
    try:
        chat = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_rules}, {"role": "user", "content": message.content}],
            model="llama-3.3-70b-versatile"
        )
        await message.reply(chat.choices[0].message.content)
    except:
        await message.reply("*ก้มหน้าสำนึกผิด*\n\nเซร่าประมวลผลไม่ทันค่ะท่านน้ำมนต์ 💢")

# --- 📜 Commands ---
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.reply("*เดินเข้าห้องสายเสียงอย่างสง่างาม*\n\nเซร่ามาสแตนด์บายรอรับใช้ท่านแล้วค่ะ 💙")
    else: await ctx.reply("💢 กรุณาเข้าสายสนทนาก่อนนะคะ!")

@bot.command()
async def music(ctx):
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs: return await ctx.reply("เซร่าหาแผ่นเสียงไม่เจอเลยค่ะ 💢")
    await ctx.reply("*กางรายชื่อเพลง*\n\nท่านน้ำมนต์อยากฟังเพลงไหนคะ?", view=MusicButtons(songs))

@bot.command()
async def test(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.reply("*ตรวจสอบระบบ*\n\nเซร่าพร้อมรับใช้ท่านน้ำมนต์ 100% แล้วค่ะ! 💙")

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดทำความสะอาดห้องแชท* 🧹✨", delete_after=3)

@bot.command()
async def weather(ctx):
    report = get_morning_report()
    await ctx.reply(f"*หยิบหน้าจอพยากรณ์ขึ้นมาดู*\n\n{report} นะคะ 💢")

@bot.command()
async def myname(ctx, *, name: str):
    db = load_data("user_names")
    db[str(ctx.author.id)] = name
    save_data("user_names", db)
    await ctx.reply(f"*จดบันทึกชื่อ*\n\nเซร่าจำชื่อคุณ '{name}' ไว้แล้วค่ะ 💢")

@bot.command()
async def relationship(ctx):
    if ctx.author.id == OWNER_ID:
        return await ctx.reply("*หน้าแดงจัด*\n\nสำหรับท่าน... คือ 'คลั่งรักที่สุดในโลก' ค่ะ! 💙💢")
    db = load_data("affinity")
    score = db.get(str(ctx.author.id), 0)
    status = "แย่" if score < 0 else "ดีเยี่ยม" if score >= 100 else "ดี" if score >= 50 else "เฉย"
    await ctx.reply(f"ระดับความสัมพันธ์ของคุณคือ: '{status}' ค่ะ 💢")

# --- ⚙️ Event Handling ---
@bot.event
async def on_ready():
    print(f'Sera Absolute Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🔔 **อัปเดตเพลงและระบบหัวใจดิจิทัลเสร็จสมบูรณ์**", color=0x3498db)
        embed.description = (
            "**👤 ข้อมูลเจ้าของบอท**\nท่านน้ำมนต์ (nummonrapeewit@gmail.com)\n\n"
            "**📜 รายการคำสั่ง (Public)**\n"
            "🔹 `!join` : เชิญเซร่าเข้าสายเสียง\n"
            "🔹 `!music` : เลือกเพลงมาฟัง (จากปุ่มกด) 🎵\n"
            "🔹 `!weather` : เช็คพยากรณ์อากาศ\n"
            "🔹 `!myname [ชื่อ]` : ให้เซร่าจดจำชื่อเล่น\n"
            "🔹 `!relationship` : เช็คระดับใจ\n"
            "🔹 `!draw [ข้อความ]` : สั่งเซร่าวาดรูป\n"
        )
        await channel.send("✨ **เซร่าอัปเดตระบบและคืนหัวใจประมวลผลเสร็จแล้วค่ะ!**", embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if not await anti_spam_check(message): return

    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    # สะสมแต้ม (สำหรับคนอื่น)
    if not is_owner:
        db = load_data("affinity")
        score = 10 if any(x in message.content for x in ["ขอบคุณ", "น่ารัก", "เก่ง"]) else \
               -15 if any(x in message.content for x in ["โง่", "นิสัยไม่ดี", "เกลียด"]) else 0
        if score != 0:
            db[uid] = db.get(uid, 0) + score
            save_data("affinity", db)

    # ระบบ AI คุยเล่น (Tag หรือ DM)
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        await sera_ai_response(message, is_owner, uid)

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
