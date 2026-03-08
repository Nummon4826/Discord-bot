import discord
import os
import datetime
import pytz
import requests
from groq import Groq
from discord.ext import commands, tasks

# --- ตั้งค่า Config จาก Railway ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบความจำ (Memory) เก็บ 10 ข้อความล่าสุด
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

# --- ฟังก์ชันพยากรณ์อากาศแบบละเอียด ---
def get_weather(city="Bangkok"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        
        temp_current = res['main']['temp']
        temp_max = res['main']['temp_max']
        temp_min = res['main']['temp_min']
        description = res['weather'][0]['description']
        
        rain_status = "วันนี้มีโอกาสเห็นฝนนะคะ เตรียมร่มด้วยล่ะ" if "ฝน" in description else "วันนี้ไม่มีฝนค่ะ"
        
        report = (
            f"\n☁️ สภาพท้องฟ้า: {description}\n"
            f"🌡️ อุณหภูมิตอนนี้: {temp_current}°C\n"
            f"📈 สูงสุด: {temp_max}°C / 📉 ต่ำสุด: {temp_min}°C\n"
            f"☔ {rain_status}"
        )
        return report
    except:
        return "เช็คสภาพอากาศไม่ได้น่ะสิ! *จิ๊ปาก* (ดูเหมือน API Key จะมีปัญหาหรือใส่ชื่อเมืองผิดนะคะ)"

# --- คำสั่งเช็คอากาศแบบกดเอง ---
@bot.command(name="checkweather")
async def checkweather(ctx):
    weather_info = get_weather("Bangkok")
    await ctx.reply(f"นี่คือสภาพอากาศที่ไปเช็คมาให้ค่ะ: {weather_info} ...ไม่ได้อยากทำให้นะ แต่นายท่านสั่งนี่นา! *สะบัดหน้าใส่*")

# --- ระบบแจ้งเตือนอัตโนมัติ 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def morning_weather():
    # --- สำคัญ: เปลี่ยนเลขข้างล่างนี้เป็น Channel ID ของนายท่าน ---
    CHANNEL_ID = 1299667544814391349 
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        weather = get_weather("Bangkok")
        await channel.send(f"ตื่นได้แล้วค่ะ นายท่านน้ำมนต์! *เคาะประตูห้องรัวๆ* อากาศวันนี้คือ: {weather} \nไม่ได้เป็นห่วงหรอกนะ! แค่ไม่อยากให้ไปสายเฉยๆ! *สะบัดผม*")

@bot.event
async def on_ready():
    # ยืนยันสถานะออนไลน์
    print(f'Logged in as {bot.user.name} — พร้อมรับใช้นายท่านน้ำมนต์แล้วค่ะ!')
    if not morning_weather.is_running():
        morning_weather.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # อนุญาตให้ใช้คำสั่ง !checkweather ได้
    await bot.process_commands(message)

    # ตอบเมื่อโดน Tag หรือ DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()

        # บันทึกลง Memory
        if user_id not in user_memory: user_memory[user_id] = []
        user_memory[user_id].append({"role": "user", "content": user_input})
        
        # ดึงประวัติ 10 ข้อความล่าสุดมาคุย
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
            # แจ้งเตือนกรณี API Key มีปัญหา
            print(f"Error: {e}")
            await message.reply("*ลนลาน* ระบบรวนหมดแล้ว! อย่าจ้องจับผิดกันสิ! *ปิดหน้าจอหนี*")

bot.run(DISCORD_TOKEN)
