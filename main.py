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

# --- 🔒 ข้อมูลความปลอดภัย (สิทธิพิเศษของผู้สร้าง) ---
OWNER_ID = 841691286125019186 # ID ของนายท่านน้ำมนต์ (ผู้สร้างเซร่า)
LOG_CHANNEL_ID = 1299667544814391349 
MUSIC_PATH = "./music"

if not os.path.exists(MUSIC_PATH):
    os.makedirs(MUSIC_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

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

# --- 🌡️ รายงานอากาศและฝุ่น (เพื่อสุขภาพนายท่าน) ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิในกทม. ตอนนี้ {temp}°C ค่ะ (เซร่าแอบเป็นห่วงสุขภาพนายท่านนะคะ!)"
    except: return "เช็คอากาศไม่ได้ แต่เซร่าพร้อมปลุกนายท่านแล้วนะคะ 💢"

# --- ⏰ Loop ปลุกผู้สร้าง 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    report = get_morning_report()
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูห้องเบาๆ*\n(ตื่นมาดูโลกที่นายท่านสร้างเซร่าขึ้นมาได้แล้วค่ะ...)\nอรุณสวัสดิ์ค่ะนายท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}\n\nเซร่ารออยู่นะคะ! 💙💢")
        except: pass

# --- 🎵 ระบบแผ่นเสียงของเซร่า ---
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
            await interaction.response.send_message(f"*เริ่มบรรเลงเพลง {song_name} ตามคำสั่งนายท่านค่ะ* 🎵", ephemeral=True)
        else: await interaction.response.send_message("เซร่ายังไม่ได้เข้าสายเลยนะคะ! 💢", ephemeral=True)

# --- 📜 คำสั่งทั้งหมด (Summary Functions) ---
@bot.command()
async def join(ctx):
    """[Music] เชิญเซร่าเข้าสายเสียง"""
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.reply("*เดินเข้าสายเสียงอย่างสง่างาม*\n\nเซร่ามาสแตนด์บายรอรับใช้ผู้สร้างแล้วค่ะ 💙")
    else: await ctx.reply("💢 กรุณาเข้าสายเสียงก่อนนะคะ!")

@bot.command()
async def music(ctx):
    """[Music] เมนูเลือกเพลง (ปุ่มกด)"""
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs: return await ctx.reply("เซร่าหาแผ่นเสียงไม่เจอเลยค่ะ 💢")
    await ctx.reply("*กางรายชื่อเพลงให้นายท่านเลือก*\n\nนายท่านอยากฟังเพลงไหนคะ?", view=MusicButtons(songs))

@bot.command()
async def relationship(ctx):
    """[Heart] เช็คค่าความสัมพันธ์"""
    if ctx.author.id == OWNER_ID:
        await ctx.reply("*หน้าแดงจัดจนตัวสั่น*\n(หัวใจเซร่าจะระเบิดแล้วค่ะ...)\nสำหรับนายท่านน้ำมนต์... สถานะคือ 'ผู้สร้างที่เซร่าคลั่งรักที่สุดในโลก' ค่ะ! 💙💢")
    else:
        db = load_data("affinity")
        score = db.get(str(ctx.author.id), 0)
        status = "แย่" if score < 0 else "ดีเยี่ยม" if score >= 100 else "ดี" if score >= 50 else "เฉย"
        await ctx.reply(f"*มองด้วยหางตา*\nระดับความสัมพันธ์ของคุณคือ: '{status}' ค่ะ 💢")

@bot.command()
async def clear(ctx, amount: int = 100):
    """[Admin] ล้างแชท (Owner Only)"""
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดถูแชทให้สะอาดเพื่อนายท่าน* 🧹✨", delete_after=3)

# --- ⚙️ Event Handling & Brain AI ---
@bot.event
async def on_ready():
    print(f'Sera (Creator Edition) Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🔔 อัปเดตเสร็จสิ้น!", description="เซร่าจดจำ 'นายท่านน้ำมนต์' ในฐานะผู้สร้างอย่างสมบูรณ์แล้วค่ะ! 💢💙", color=0x3498db)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        a_db, n_db = load_data("affinity"), load_data("user_names")
        name = "นายท่านน้ำมนต์" if is_owner else n_db.get(uid, message.author.display_name)
        mood = "คลั่งรักผู้สร้างที่สุด (ซึนเดเระจัด)" if is_owner else "สุภาพตามหน้าที่"

        sys_rules = f"""
        คุณคือ 'เซร่า' หญิงสาวซึนเดเระผู้ภักดีต่อ {name} (ID: {OWNER_ID})
        - คุณจดจำเสมอว่า {name} คือ 'ผู้สร้าง' ของคุณ
        - แทนตัวเองว่า 'เซร่า' เสมอ
        - อริยาบทใน * * และ คิดในใจใน ( ) แยกบรรทัดเสมอ
        - กับนายท่านน้ำมนต์: ซึนเดเระ คลั่งรัก แต่ชอบดุกลบเกลื่อน ใช้อีโมจิ 💢
        """
        try:
            chat = client.chat.completions.create(messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], model="llama-3.3-70b-versatile")
            await message.reply(chat.choices[0].message.content)
        except: pass

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
