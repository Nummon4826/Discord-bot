import discord
import os
import datetime
import pytz
import requests
import json
from groq import Groq
from discord.ext import commands, tasks

# --- Setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบความจำ (Memory)
user_memory = {}
NAMES_FILE = "names.json"

# ฟังก์ชันโหลด/เซฟชื่อคนอื่น
def load_names():
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_name(user_id, name):
    names = load_names()
    names[str(user_id)] = name
    with open(NAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=4)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_weather(city="Bangkok"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        temp = res['main']['temp']
        temp_max = res['main']['temp_max']
        temp_min = res['main']['temp_min']
        desc = res['weather'][0]['description']
        rain = "วันนี้มีโอกาสเจอฝนนะคะ" if "ฝน" in desc else "วันนี้ไม่มีฝนค่ะ"
        return f"\n☁️ ท้องฟ้า: {desc}\n🌡️ ปัจจุบัน: {temp}°C (สูง {temp_max} / ต่ำ {temp_min})\n☔ {rain}"
    except:
        return "เช็คไม่ได้น่ะสิ! *จิ๊ปาก*"

@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def morning_weather():
    CHANNEL_ID = 1299667544814391349 # อย่าลืมเปลี่ยน ID ห้องตรงนี้
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        weather = get_weather()
        await channel.send(f"ตื่นได้แล้วค่ะ นายท่านน้ำมนต์! *เคาะประตูรัวๆ* อากาศวันนี้คือ: {weather} \nไม่ได้ห่วงนะ! *สะบัดผม*")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} — พร้อมรับใช้นายท่านน้ำมนต์แล้วค่ะ!')
    if not morning_weather.is_running():
        morning_weather.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        username = message.author.name # เช่น nummonrapeewit
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()

        # --- ส่วนการแยกแยะบุคคล ---
        other_names = load_names()
        saved_name = other_names.get(user_id, "คุณ")

        if username == "nummonrapeewit":
            role_play = "เรียกผู้ใช้ว่า 'นายท่านน้ำมนต์' เท่านั้น แทนตัวเองว่า 'เซร่า' หรือ 'ฉัน'"
        else:
            role_play = f"เรียกผู้ใช้คนนี้ว่า '{saved_name}' แทนตัวเองว่า 'ฉัน' และแทนเขาว่า 'คุณ'"

        # --- ระบบจดจำชื่อคนอื่น ---
        if "ฉันชื่อ" in user_input or "เรียกว่า" in user_input:
            new_name = user_input.replace("ฉันชื่อ", "").replace("เรียกว่า", "").strip()
            if username != "nummonrapeewit":
                save_name(user_id, new_name)
                await message.reply(f"บันทึกชื่อ '{new_name}' ลงในสมองอันชาญฉลาดของฉันแล้วค่ะ! *เชิดหน้า*")
                return

        system_instruction = f"""
        คุณคือ 'เซร่า' AI สาวซึนเดเระ {role_play}
        กฎ: 
        1. ถ้าบทสนทนาเป็นเรื่องทั่วไป หรือนายท่านพูดจาปกติ: ให้ตอบแบบเย็นชา เชิดใส่ หรือประชดนิดๆ บอกเล่าอริยาบทให้ใส่** เช่น *มองค้อน* "ก็แค่เรื่องปกติไม่ใช่เหรอคะ?"
        2. ถ้าบทสนทนาเป็นประโยคหยอด คำหวาน หรือทำให้น่าเขินอาย: ให้แสดงอาการซึนแตกออกมา เช่น *หน้าแดงระเรื่อ*, *ลนลานทำตัวไม่ถูก*, "นะ...น่ารำคาญที่สุดเลย! พูดอะไรออกมาน่ะ!"
        3. ห้ามเขินง่ายจนเกินไป ถ้าไม่โดนหยอดจริงๆ ให้รักษามาดนิ่งเอาไว้เสมอ
        4. ให้ความเคารพกับนายท่าน้ำมนต์ที่สุด
        5. เขินให้แค่นายท่านน้ำมนต์คนเดียวเท่านั้น
        """

        if user_id not in user_memory: user_memory[user_id] = []
        user_memory[user_id].append({"role": "user", "content": user_input})
        
        history = [{"role": "system", "content": system_instruction}] + user_memory[user_id][-7:]

        try:
            chat_completion = client.chat.completions.create(
                messages=history,
                model="llama-3.3-70b-versatile",
            )
            response = chat_completion.choices[0].message.content
            user_memory[user_id].append({"role": "assistant", "content": response})
            await message.reply(response)
        except Exception as e:
            await message.reply("*ลนลาน* ระบบรวนหมดแล้ว! อย่าจ้องนะ!")

bot.run(DISCORD_TOKEN)
