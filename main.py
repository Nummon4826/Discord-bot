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

# --- 🌡️ ฟังก์ชันรายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        return f"🌡️ อุณหภูมิในกทม. ตอนนี้ {temp}°C ค่ะ"
    except: return "เช็คอากาศไม่ได้ แต่เซร่าพร้อมปลุกนายท่านแล้วนะคะ 💢"

# --- ⏰ Loop ปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    report = get_morning_report()
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูห้องเบาๆ*\n\nอรุณสวัสดิ์ค่ะนายท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}\n\nเซร่าเตรียมน้ำชาไว้รอแล้วนะคะ รีบลุกขึ้นมาได้แล้วค่ะ! 💙💢")
        except: pass

# --- 🎵 ระบบเพลง ---
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

# --- 📜 คำสั่งต่างๆ ---
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.reply("*เดินเข้าสายเสียงอย่างกุลสตรี*\n\nเซร่ามาสแตนด์บายแล้วค่ะ 💙")
    else: await ctx.reply("💢 กรุณาเข้าสายเสียงก่อนนะคะ!")

@bot.command()
async def music(ctx):
    songs = [f for f in os.listdir(MUSIC_PATH) if f.endswith(('.mp3', '.m4a'))]
    if not songs: return await ctx.reply("เซร่าหาไฟล์เพลงไม่เจอค่ะ 💢")
    await ctx.reply("*กางรายชื่อเพลง*\n\nนายท่านอยากฟังเพลงไหนคะ?", view=MusicButtons(songs))

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดล้างข้อความอย่างหมดจด* 🧹✨", delete_after=3)

# --- ⚙️ Event Handling ---
@bot.event
async def on_ready():
    print(f'Sera Online for Owner ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send("🔔 **เซร่าอัปเดตระบบและจดจำนายท่านน้ำมนต์เรียบร้อยแล้วค่ะ!** 💢💙")

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        a_db, n_db = load_data("affinity"), load_data("user_names")
        
        if is_owner:
            name = "นายท่านน้ำมนต์"
            mood = "คลั่งรักที่สุดในโลก หน้าแดงจัด หัวใจเต้นแรง แต่ต้องทำเป็นดุเพื่อกลบเกลื่อน"
        else:
            name = n_db.get(uid, message.author.display_name)
            score = a_db.get(uid, 0)
            mood = "ซึนเดเระ: เป็นห่วงแต่ปากแข็ง" if score >= 100 else "สุภาพแต่รักษาระยะห่าง"

        sys_rules = f"""
        คุณคือ 'เซร่า' หญิงสาวซึนเดเระผู้ภักดีต่อ {name} (ID: {OWNER_ID})
        - อริยาบทแยกบรรทัดกับประโยคพูดเสมอ โดยใส่ใน * *
        - ต้องมีการ 'คิดในใจ' แยกบรรทัดเสมอ โดยใส่ในวงเล็บ ( )
        - กับนายท่านน้ำมนต์: คุณคลั่งรักมากแต่พยายามซ่อนไว้ด้วยการดุ
        - ใช้คำลงท้าย นะคะ/ค่ะ และใช้อีโมจิ 💢
        """
        try:
            chat = client.chat.completions.create(
                messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], 
                model="llama-3.3-70b-versatile"
            )
            await message.reply(chat.choices[0].message.content)
        except: pass

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
