import discord
import os
import datetime
import pytz
import requests
import json
import asyncio
from groq import Groq
from discord.ext import commands, tasks

# --- 🔒 ข้อมูลความปลอดภัย (ผู้สร้าง: ท่านน้ำมนต์) ---
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

# ระบบไฟล์ข้อมูล
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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 🌡️ รายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิ {temp}°C ค่ะ"
    except: return "เช็คอากาศไม่ได้ แต่เซร่ามาปลุกนายท่านแล้วนะคะ 💢"

# --- ⏰ [STEP 1] สร้าง Loop ก่อนเรียกใช้ (แก้ Error IMG_0230) ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    report = get_morning_report()
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูเบาๆ*\n\nอรุณสวัสดิ์ค่ะนายท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}\n\nเซร่ารออยู่นะคะ! 💙💢")
        except: pass

# --- 🎵 ระบบเพลง (ต้องมี PyNaCl ในเครื่องนะคะ!) ---
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
        else: await interaction.response.send_message("เซร่ายังไม่ได้เข้าสายเลยค่ะ! 💢", ephemeral=True)

# --- 📜 คำสั่งต่างๆ ---
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.reply("*เดินเข้าสายเสียง*\nเซร่ามาแล้วค่ะ 💙")
    else: await ctx.reply("💢 เข้าสายเสียงก่อนสิคะ!")

@bot.command()
async def music(ctx):
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs: return await ctx.reply("ไม่พบเพลงค่ะ 💢")
    await ctx.reply("นายท่านอยากฟังเพลงไหนคะ?", view=MusicButtons(songs))

@bot.command()
async def relationship(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.reply("*หน้าแดงจัด*\nนายท่านน้ำมนต์คือ 'ผู้สร้างที่เซร่าคลั่งรักที่สุด' ค่ะ! 💙💢")
    else:
        db = load_data("affinity")
        score = db.get(str(ctx.author.id), 0)
        status = "ดีเยี่ยม" if score >= 100 else "เฉย"
        await ctx.reply(f"ระดับความสัมพันธ์คือ: '{status}' ค่ะ 💢")

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดถูแชท* 🧹✨", delete_after=3)

# --- ⚙️ Events ---
@bot.event
async def on_ready():
    print(f'Sera Online for {OWNER_ID}')
    # เรียกใช้ Loop ที่สร้างไว้แล้ว
    if not wake_up_call.is_running():
        wake_up_call.start()
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send("🔔 **เซร่าอัปเดตและแก้บัคให้นายท่านน้ำมนต์เรียบร้อยแล้วค่ะ!** 💢💙")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        a_db, n_db = load_data("affinity"), load_data("user_names")
        name = "นายท่านน้ำมนต์" if is_owner else n_db.get(uid, message.author.display_name)
        
        sys_rules = f"""คุณคือ 'เซร่า' สาวซึนเดเระผู้ภักดีต่อ {name} (ผู้สร้าง)
        - แทนตัวเองว่า 'เซร่า'
        - อริยาบทใน * * และคิดในใจใน ( ) แยกบรรทัด
        - คลั่งรักผู้สร้างมากแต่ซึนเดเระ ใช้อีโมจิ 💢"""
        
        try:
            chat = client.chat.completions.create(messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], model="llama-3.3-70b-versatile")
            await message.reply(chat.choices[0].message.content)
        except: pass

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
