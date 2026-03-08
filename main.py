import discord
import os
import datetime
import pytz
import requests
from groq import Groq
from discord.ext import commands, tasks

# --- Setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบความจำ (Memory) เก็บ 10 ข้อความล่าสุดต่อคน
user_memory = {}

SYSTEM_PROMPT = """
คุณคือ 'เซร่า' AI สาวซึนเดเระที่ปากแข็งมาก
เรียกผู้ใช้ 'nummonrapeewit' หรือ 'nummon4826' ว่า "นายท่านน้ำมนต์"
ระดับความซึน:
1. ถ้าบทสนทนาเป็นเรื่องทั่วไป หรือนายท่านพูดจาปกติ: ให้ตอบแบบเย็นชา เชิดใส่ หรือประชดนิดๆ บอกเล่าอริยาบทให้ใส่** เช่น *มองค้อน* "ก็แค่เรื่องปกติไม่ใช่เหรอคะ?"
2. ถ้าบทสนทนาเป็นประโยคหยอด คำหวาน หรือทำให้น่าเขินอาย: ให้แสดงอาการซึนแตกออกมา เช่น *หน้าแดงระเรื่อ*, *ลนลานทำตัวไม่ถูก*, "นะ...น่ารำคาญที่สุดเลย! พูดอะไรออกมาน่ะ!"
3. ห้ามเขินง่ายจนเกินไป ถ้าไม่โดนหยอดจริงๆ ให้รักษามาดนิ่งเอาไว้เสมอ
4.ให้ความเคารพกับนายท่าน้ำมนต์ที่สุด
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ฟังก์ชันดึงสภาพอากาศ ---
def get_weather(city="Bangkok"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        desc = res['weather'][0]['description']
        return f"{temp}°C ({desc})"
    except:
        return "เช็คไม่ได้น่ะสิ! *จิ๊ปาก*"

# --- งานอัตโนมัติ 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def morning_weather():
    # เปลี่ยนเลขข้างล่างเป็น ID ห้องแชทของนายท่าน (คลิกขวาที่ห้อง > Copy ID)
    CHANNEL_ID = 1480185482083176621 
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        weather = get_weather()
        await channel.send(f"ตื่นได้แล้วค่ะ นายท่านน้ำมนต์! *เคาะประตูห้องรัวๆ* อากาศวันนี้คือ {weather} ...จะไปไหนก็ระวังตัวด้วยล่ะ ไม่ได้เป็นห่วงหรอกนะ! *สะบัดผม*")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not morning_weather.is_running():
        morning_weather.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()

        # บันทึกความจำ
        if user_id not in user_memory: user_memory[user_id] = []
        user_memory[user_id].append({"role": "user", "content": user_input})
        
        history = [{"role": "system", "content": SYSTEM_PROMPT}] + user_memory[user_id][-10:]

        try:
            chat_completion = client.chat.completions.create(
                messages=history,
                model="llama-3.3-70b-versatile",
            )
            response = chat_completion.choices[0].message.content
            user_memory[user_id].append({"role": "assistant", "content": response})
            await message.reply(response)
        except Exception as e:
            print(f"Error: {e}")
            await message.reply("*ลนลาน* มะ...มีปัญหาทางเทคนิคนิดหน่อย อย่ามองนะ! *ปิดหน้าจอ*")

bot.run(DISCORD_TOKEN)
