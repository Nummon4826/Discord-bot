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

# --- 🔒 ตั้งค่าความปลอดภัย ---
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

DATA_FILES = {"affinity": "affinity.json", "user_names": "user_names.json", "status": "status.json"}
for f in DATA_FILES.values():
    if not os.path.exists(f): 
        with open(f, "w", encoding="utf-8") as file: json.dump({}, file)

def load_data(key):
    with open(DATA_FILES[key], "r", encoding="utf-8") as f: return json.load(f)

def save_data(key, data):
    with open(DATA_FILES[key], "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ตารางสอบและรายงานอากาศ ---
SPECIAL_DATES = {
    "20260314": "*กุมมือท่านเบาๆ*\n\nวันนี้สอบ A-Level วันแรก สู้ๆ นะคะท่านน้ำมนต์ 💙",
    "20260315": "*ส่งยิ้มให้*\n\nA-Level วันที่สองแล้ว พักผ่อนเยอะๆ นะคะ 💢",
    "20260316": "*รอรับกลับบ้าน*\n\nวันสุดท้ายของ A-Level แล้วนะคะ! 💙",
    "20260321": "*จัดเสื้อให้*\n\nสอบตรงพระนครเหนือ 07:00 น. เดินทางปลอดภัยค่ะ! ⚙️"
}

def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิตอนนี้ {temp}°C ค่ะ"
    except: return "เช็คอากาศไม่ได้ แต่เซร่ามาปลุกท่านแล้วค่ะ 💢"

# --- [FIXED] Loop ปลุก ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    now_str = datetime.datetime.now(TIMEZONE).strftime("%Y%m%d")
    report = get_morning_report()
    special = f"\n\n{SPECIAL_DATES.get(now_str, '')}" if now_str in SPECIAL_DATES else ""
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try: await member.send(f"*เคาะประตู*\n\nอรุณสวัสดิ์ค่ะท่านน้ำมนต์\n\n{report}{special}\n\nเซร่ารออยู่นะคะ 💙💢")
        except: pass

# --- ระบบเพลง ---
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
            await interaction.response.send_message(f"*เริ่มบรรเลงเพลง {song_name} ค่ะ* 🎵", ephemeral=True)
        else: await interaction.response.send_message("เซร่ายังไม่ได้เข้าสายสนทนาเลยนะคะ! 💢", ephemeral=True)

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.reply("*เดินเข้าห้องสนทนาอย่างกุลสตรี*\n\nเซร่ามาแล้วค่ะ 💙")
    else: await ctx.reply("💢 กรุณาเข้าสายเสียงก่อนนะคะ!")

@bot.command()
async def music(ctx):
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs: return await ctx.reply("เซร่าหาแผ่นเสียงไม่เจอเลยค่ะ 💢")
    await ctx.reply("*กางรายชื่อเพลง*\n\nท่านน้ำมนต์อยากฟังเพลงไหนคะ?", view=MusicButtons(songs))

# --- [FIXED] คืนคำสั่งลับของเจ้าของ ---
@bot.command()
async def test(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.reply("*ตรวจสอบระบบ*\n\nเซร่าพร้อมรับใช้ท่านน้ำมนต์ 100% แล้วค่ะ! 💙")

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดล้างข้อความอย่างหมดจด* 🧹✨", delete_after=3)

@bot.command()
async def myname(ctx, *, name: str):
    db = load_data("user_names")
    db[str(ctx.author.id)] = name
    save_data("user_names", db)
    await ctx.reply(f"*จดบันทึก*\n\nเซร่าจำชื่อคุณ '{name}' ไว้แล้วค่ะ 💢")

@bot.command()
async def relationship(ctx):
    if ctx.author.id == OWNER_ID:
        return await ctx.reply("*หน้าแดงจัด*\n\nสถานะคือ 'คลั่งรักที่สุดในโลก' ค่ะ! 💙💢")
    db = load_data("affinity")
    score = db.get(str(ctx.author.id), 0)
    status = "แย่" if score < 0 else "ดีเยี่ยม" if score >= 100 else "ดี" if score >= 50 else "เฉย"
    await ctx.reply(f"ระดับความสัมพันธ์ของคุณคือ: '{status}' ค่ะ 💢")

# --- ระบบรายงานอัปเดต ---
@bot.event
async def on_ready():
    print(f'Sera Complete Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="✨ **อัปเดตเพลงและระบบเสียงเสร็จสมบูรณ์**", color=0x3498db)
        embed.description = (
            "**👤 ข้อมูลเจ้าของ**\nท่านน้ำมนต์ (nummonrapeewit@gmail.com)\n\n"
            "**📜 คำสั่งคนทั่วไป**\n"
            "🔹 `!join` : เชิญเซร่าเข้าสายเสียง\n"
            "🔹 `!music` : เลือกเพลงมาฟัง 🎵\n"
            "🔹 `!weather` : เช็คอากาศ\n"
            "🔹 `!myname [ชื่อ]` : ให้เซร่าจำชื่อ\n"
            "🔹 `!relationship` : เช็คความสัมพันธ์\n"
            "🔹 `!draw [ข้อความ]` : สั่งวาดรูป\n"
        )
        await channel.send("🔔 **อัปเดตเพลงและแก้ไขระบบเสียงเรียบร้อยแล้วค่ะ!**", embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    # ระบบ AI และความสัมพันธ์ใส่ต่อที่นี่ได้เลยค่ะ
    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
