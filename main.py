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
MUSIC_PATH = "./music"  # โฟลเดอร์เก็บไฟล์เพลง (.mp3)

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

# --- ระบบเพลง (Music System) ---
class MusicButtons(discord.ui.View):
    def __init__(self, songs):
        super().__init__(timeout=60)
        for i, song in enumerate(songs[:25]): # แสดงสูงสุด 25 เพลง
            button = discord.ui.Button(label=f"{i+1}. {song[:20]}", style=discord.ButtonStyle.primary, custom_id=song)
            button.callback = self.play_callback
            self.add_item(button)

    async def play_callback(self, interaction: discord.Interaction):
        song_name = interaction.data['custom_id']
        voice = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice and voice.is_connected():
            if voice.is_playing():
                voice.stop()
            source = discord.FFmpegPCMAudio(os.path.join(MUSIC_PATH, song_name))
            voice.play(source)
            await interaction.response.send_message(f"*เริ่มบรรเลงเพลง {song_name} ให้ท่านฟังแล้วค่ะ* 🎵💢", ephemeral=True)
        else:
            await interaction.response.send_message("เซร่ายังไม่ได้เข้าสายสนทนาเลยนะคะ! 💢", ephemeral=True)

@bot.command()
async def join(ctx):
    """สั่งให้เซร่าเข้าสายสนทนา"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.reply("*เดินเข้าห้องสนทนาอย่างเงียบเชียบ*\n\nเซร่าเข้ามาแสตนด์บายรอรับใช้ท่านแล้วค่ะ 💙")
    else:
        await ctx.reply("💢 กรุณาเข้าสายสนทนาก่อนนะคะ!")

@bot.command()
async def leave(ctx):
    """สั่งให้เซร่าออกจากสายสนทนา"""
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        await voice.disconnect()
        await ctx.reply("*ย่อตัวลา*\n\nเซร่าขอตัวไปจัดการงานบ้านต่อนะคะ 💢")

@bot.command()
async def music(ctx):
    """แสดงรายชื่อเพลงและกดเลือกเล่น"""
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs:
        return await ctx.reply("ไม่พบไฟล์เพลงในระบบเลยค่ะท่านน้ำมนต์ 💢")
    
    view = MusicButtons(songs)
    await ctx.reply("*กางรายชื่อแผ่นเสียงที่มี*\n\nท่านต้องการฟังเพลงไหนดีคะ? เลือกได้เลยค่ะ!", view=view)

# --- รายงานอัปเดตและคู่มือการใช้งาน ---
async def send_update_report():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="✨ **อัปเดตระบบ: Sera V.Supreme Music Edition**", color=0x3498db)
        embed.description = (
            "เซร่าอัปเดตระบบเสร็จสมบูรณ์แล้วค่ะ! เพิ่มระบบความสัมพันธ์และระบบเครื่องเล่นเพลงเรียบร้อยแล้ว\n\n"
            "**👤 ข้อมูลเจ้าของบอท**\n"
            "ท่านน้ำมนต์ (Nummon Rapeewit)\n"
            "📧 nummonrapeewit@gmail.com\n\n"
            "**📜 คำสั่งสำหรับบุคคลทั่วไป (Public)**\n"
            "🔹 `!hello` : แนะนำตัวกุลสตรีเซร่า\n"
            "🔹 `!weather` : เช็คอากาศและ PM2.5\n"
            "🔹 `!myname [ชื่อ]` : ให้เซร่าจดจำชื่อเล่นคุณ\n"
            "🔹 `!relationship` : เช็คค่าความสัมพันธ์ (แย่/เฉย/ดี/ดีเยี่ยม)\n"
            "🔹 `!join` : เชิญเซร่าเข้าสายสนทนา\n"
            "🔹 `!music` : เลือกเล่นเพลงจากไฟล์ของเซร่า 🎵\n"
            "🔹 `!draw [ข้อความ]` : สั่งเซร่าวาดรูป\n\n"
            "**💖 สถานะพิเศษของท่านน้ำมนต์**\n"
            "เซร่าจะคลั่งรักท่านคนเดียว และคำสั่งลับ (Clear/Test) จะไม่ปรากฏที่นี่ค่ะ 💢"
        )
        embed.set_footer(text="เซร่าพร้อมดูแลท่านน้ำมนต์แล้วค่ะ 💙")
        await channel.send("🔔 **อัปเดตเพลงและระบบหัวใจดิจิทัลเสร็จสิ้นแล้วค่ะ!**", embed=embed)

# --- (on_ready และ on_message ใช้ส่วนเดิมจากข้อความที่แล้ว) ---
@bot.event
async def on_ready():
    print(f'Sera Music System Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    await send_update_report()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    # ... (ส่วนกันสแปมและ AI Response จากโค้ดก่อนหน้า) ...
    await bot.process_commands(message)

# --- (Loop ปลุก 06:00 น. และระบบความสัมพันธ์ใส่กลับเข้าไปตามโค้ดก่อนหน้า) ---
bot.run(DISCORD_TOKEN)
