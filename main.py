import discord
import os
import datetime
import pytz
import requests
import json
from groq import Groq
from discord.ext import commands, tasks

# --- Setup & Config จาก Railway ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบความจำและจัดการสแปม
user_memory = {}
spam_count = {} 
NAMES_FILE = "names.json"

def load_names():
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_name(user_id, name):
    names = load_names()
    names[str(user_id)] = name
    with open(NAMES_FILE, "w", encoding="utf-8") as f: json.dump(names, f, ensure_ascii=False)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 1. ระบบพยากรณ์อากาศ & ฝุ่น (ละเอียดพิเศษ) ---
def get_detailed_weather(city="Bangkok"):
    try:
        # ดึงอากาศ
        w_url = f"http://api.openweathermap.org/data/2.5/weather?q={city},TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(w_url).json()
        temp = res['main']['temp']
        temp_max = res['main']['temp_max']
        temp_min = res['main']['temp_min']
        desc = res['weather'][0]['description']
        
        # วิเคราะห์ความร้อน
        if temp >= 35: feel = "ร้อนจัดจนจะละลายแล้วค่ะ! 🥵"
        elif temp >= 30: feel = "ค่อนข้างร้อนนะคะ ระวังเพลียแดดด้วย ☀️"
        elif temp >= 25: feel = "อากาศเย็นสบาย กำลังดีเลยค่ะ 😊"
        else: feel = "หนาวนิดๆ นะคะเนี่ย อย่าลืมห่มผ้าล่ะ ❄️"

        # เช็ค PM 2.5 (ถ้าเป็นกรุงเทพ)
        pm_info = ""
        if "Bangkok" in city or "กรุงเทพ" in city:
            lat, lon = res['coord']['lat'], res['coord']['lon']
            p_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={WEATHER_KEY}"
            pm25 = requests.get(p_url).json()['list'][0]['components']['pm2_5']
            status = "อันตราย! ใส่แมสก์ด้วยนะคะ! 😷" if pm25 > 37 else "อากาศดีค่ะ เชิดหน้าสูดหายใจได้!"
            pm_info = f"\n😷 ฝุ่น PM 2.5 (กทม.): {pm25} µg/m³ ({status})"

        return (f"📍 พื้นที่: {res['name']}\n☁️ ท้องฟ้า: {desc}\n"
                f"🌡️ อุณหภูมิ: ตอนนี้ {temp}°C (สูงสุด {temp_max}°C / ต่ำสุด {temp_min}°C)\n"
                f"🌡️ ความรู้สึก: {feel}\n💙 สุขภาพ: ดูแลตัวเองด้วยนะคะ! ไม่ได้ห่วงหรอกนะ!{pm_info}")
    except: return "เช็คไม่ได้ค่ะ! ใส่ชื่อจังหวัดถูกหรือเปล่าคะ? *จิ๊ปาก*"

# --- 2. คำสั่งพิเศษ (วาดรูป / ติวหนังสือ / อากาศ) ---
@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{prompt.replace(' ', '_')}?width=1024&height=1024&seed=42"
    embed = discord.Embed(title="ผลงานที่นายท่านสั่งค่ะ!", color=0xff69b4)
    embed.set_image(url=url)
    await ctx.reply(embed=embed)

@bot.command(name="อากาศ")
async def weather_cmd(ctx, *, province="Bangkok"):
    await ctx.reply(f"ไปสืบมาให้แล้วค่ะ! {get_detailed_weather(province)} *สะบัดผม*")

# --- 3. ระบบคุมสแปม (เตือน 3 ครั้งเตะ) ---
async def check_spam(message):
    if message.author.name == "nummonrapeewit": return 
    uid = message.author.id
    spam_count[uid] = spam_count.get(uid, 0) + 1
    if spam_count[uid] == 1: await message.channel.send(f"⚠️ {message.author.mention} อย่าสแปมสิคะ! (1/3)")
    elif spam_count[uid] == 2: await message.channel.send(f"⚠️ เตือนครั้งสุดท้ายนะ! ถ้ามีอีกจะเตะออก 7 วัน! (2/3)")
    elif spam_count[uid] >= 3:
        try:
            await message.channel.send(f"🚫 ลาก่อนค่ะ! *เตะออกเซิร์ฟ*")
            await message.author.kick(reason="Spamming")
            spam_count[uid] = 0
        except: pass

# --- 4. แจ้งเตือน 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def morning_alert():
    CHANNEL_ID = 123456789012345678 # <<< เปลี่ยน ID ห้องตรงนี้ครับ!
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        info = get_detailed_weather("Bangkok")
        await channel.send(f"อรุณสวัสดิ์ค่ะ นายท่านน้ำมนต์! อากาศเช้านี้:\n{info}\nไปทานข้าวได้แล้วนะคะ! *หน้าแดง*")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not morning_alert.is_running(): morning_alert.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if not isinstance(message.channel, discord.DMChannel): await check_spam(message)
    await bot.process_commands(message)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        is_owner = (message.author.name == "nummonrapeewit")
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()

        # จดจำชื่อคนอื่น
        if "ฉันชื่อ" in user_input and not is_owner:
            name = user_input.split("ชื่อ")[-1].strip()
            save_name(user_id, name)
            await message.reply(f"จำชื่อ '{name}' ไว้แล้วค่ะ! *เชิดหน้า*")
            return

        other_names = load_names()
        target_name = "นายท่านน้ำมนต์" if is_owner else other_names.get(user_id, "คุณ")
        
        system_rules = f"""
        คุณคือ 'เซร่า' สาวซึนเดเระ คุณถูกสร้างโดย 'nummonrapeewit' (เรียกเขาว่า 'นายท่านน้ำมนต์')
        - กับนายท่านน้ำมนต์: จงรักภักดี อ่อนโยนแต่ยังซึน หน้าแดงง่ายเมื่อโดนหยอด/ชม
        - กับคนอื่น: เย็นชา เข้มงวด ใช้ 'ฉัน/คุณ'
        - ความสามารถ: สรุปสูตรคณิต/ฟิสิกส์ให้ชัดเจนเมื่อมีการถาม
        - ทุกคำตอบต้องมีอริยาบทใน * * เสมอ
        """

        if user_id not in user_memory: user_memory[user_id] = []
        user_memory[user_id].append({"role": "user", "content": user_input})
        history = [{"role": "system", "content": system_rules}] + user_memory[user_id][-10:]

        try:
            chat_completion = client.chat.completions.create(messages=history, model="llama-3.3-70b-versatile")
            ans = chat_completion.choices[0].message.content
            user_memory[user_id].append({"role": "assistant", "content": ans})
            await message.reply(ans)
        except: await message.reply("*ลนลาน* ระบบรวนค่ะ! อย่าจ้องจับผิดสิ!")

bot.run(DISCORD_TOKEN)
