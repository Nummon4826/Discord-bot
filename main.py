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

# --- 🔒 ข้อมูลความปลอดภัยและตั้งค่า ---
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

DATA_FILES = {"status": "status.json", "notes": "notes.json", "affinity": "affinity.json", "user_names": "user_names.json"}
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

# --- ตารางอวยพรสอบ พ.ศ. 2569 ---
SPECIAL_DATES = {
    "20260314": "*กุมมือท่านเบาๆ*\n\nวันนี้สอบ A-Level วันแรกแล้วนะคะ เซร่าขอให้ท่านมีสมาธิและทำได้ทุกข้อค่ะ สู้ๆ นะคะ 💙",
    "20260315": "*ส่งยิ้มให้กำลังใจ*\n\nA-Level วันที่สองแล้วนะคะ อย่าลืมพักผ่อนให้เพียงพอด้วยนะคะ เซร่าเป็นห่วงค่ะ 💢",
    "20260316": "*รอรับที่หน้าประตู*\n\nวันสุดท้ายของ A-Level แล้วนะคะท่านน้ำมนต์! ทำให้เต็มที่เลยค่ะ 💙",
    "20260321": "*ช่วยจัดเนคไทให้ท่าน*\n\nวันนี้สอบตรงที่พระจอมเกล้าพระนครเหนือนะคะ ต้องไปให้ทัน 07:00 น. เดินทางปลอดภัยค่ะ! ⚙️"
}

# --- ฟังก์ชันรายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิตอนนี้ {temp}°C ค่ะ"
    except: return "เช็คอากาศไม่ได้ แต่เซร่าพร้อมปลุกท่านแล้วค่ะ 💢"

# --- [FIXED] ย้ายนิยาม Loop มาไว้ก่อนใช้งาน ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    now_str = datetime.datetime.now(TIMEZONE).strftime("%Y%m%d")
    report = get_morning_report()
    special = f"\n\n{SPECIAL_DATES.get(now_str, '')}" if now_str in SPECIAL_DATES else ""
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูเบาๆ*\n\nอรุณสวัสดิ์ค่ะท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}{special}\n\nเซร่ารออยู่นะคะ 💙💢")
        except: pass

# --- ระบบเพลงและคำสั่งอื่นๆ (เหมือนเดิม) ---
class MusicButtons(discord.ui.View):
    def __init__(self, songs):
        super().__init__(timeout=60)
        for i, song in enumerate(songs[:25]):
            button = discord.ui.Button(label=f"{i+1}. {song[:20]}", style=discord.ButtonStyle.primary, custom_id=song)
            button.callback = self.play_callback
            self.add_item(button)

    async def play_callback(self, interaction: discord.Interaction):
        song_name = interaction.data['custom_id']
        voice = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice and voice.is_connected():
            if voice.is_playing(): voice.stop()
            source = discord.FFmpegPCMAudio(os.path.join(MUSIC_PATH, song_name))
            voice.play(source)
            await interaction.response.send_message(f"*เริ่มบรรเลงเพลง {song_name} ให้ท่านฟังแล้วค่ะ* 🎵💢", ephemeral=True)

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.reply("*เดินเข้าห้องสนทนาอย่างสง่างาม*\n\nเซร่าเข้ามาแสตนด์บายแล้วค่ะ 💙")
    else: await ctx.reply("💢 กรุณาเข้าสายสนทนาก่อนนะคะ!")

@bot.command()
async def music(ctx):
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs: return await ctx.reply("ไม่พบไฟล์เพลงเลยค่ะท่านน้ำมนต์ 💢")
    await ctx.reply("*กางรายชื่อแผ่นเสียงที่มี*\n\nท่านต้องการฟังเพลงไหนดีคะ?", view=MusicButtons(songs))

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดทำความสะอาด*\n\nเรียบร้อยแล้วค่ะท่านน้ำมนต์ 🧹✨", delete_after=3)

# --- ระบบจัดการอัปเดตและส่งรายงาน ---
@bot.event
async def on_ready():
    print(f'Sera Elegance Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running():
        wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🔔 อัปเดตเพลงและระบบความสัมพันธ์เสร็จสิ้น", color=0x3498db)
        embed.description = (
            "**👤 ข้อมูลผู้สร้าง**\nท่านน้ำมนต์ (nummonrapeewit@gmail.com)\n\n"
            "**📜 รายการคำสั่ง (Public)**\n"
            "🔹 `!weather` : เช็คอากาศ/ฝุ่น\n"
            "🔹 `!myname [ชื่อ]` : ให้เซร่าจดจำชื่อเล่น (ผูก ID)\n"
            "🔹 `!relationship` : เช็คระดับใจ (แย่/เฉย/ดี/ดีเยี่ยม)\n"
            "🔹 `!join` : เชิญเซร่าเข้าสายเสียง\n"
            "🔹 `!music` : เลือกเพลงจากไฟล์มาฟัง 🎵\n"
            "🔹 `!draw [ข้อความ]` : สั่งวาดรูป\n"
        )
        await channel.send("✨ **เซร่าอัปเดตระบบเสร็จแล้วค่ะ!**", embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    # (ใส่ระบบวิเคราะห์ความสัมพันธ์และ AI Response ที่นี่)
    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
