import discord
import os
import datetime
import pytz
import requests
import json
import time
from groq import Groq
from discord.ext import commands, tasks

# --- 🔒 รหัสลับยืนยันตัวตนเจ้าของ (ID ของท่านน้ำมนต์) ---
OWNER_ID = 841691286125019186 

# --- Setup API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ระบบไฟล์ข้อมูล
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
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ตารางอวยพรสอบ พ.ศ. 2569 (สไตล์กุลสตรี) ---
SPECIAL_DATES = {
    "20260314": "*กุมมือท่านเบาๆ*\n\nวันนี้สอบ A-Level วันแรกแล้วนะคะ เซร่าขอให้ท่านทำข้อสอบได้อย่างราบรื่นและมีสมาธิตลอดทั้งวันค่ะ สู้ๆ นะคะท่านน้ำมนต์ 💙",
    "20260315": "*วางถ้วยน้ำชาลงและมองหน้าท่าน*\n\nการสอบวันที่สองอาจจะเหนื่อยหน่อยนะคะ แต่เซร่าเชื่อมั่นในตัวท่านเสมอค่ะ กลับมาแล้วเซร่าจะเตรียมรางวัลไว้ให้นะคะ 💢",
    "20260316": "*ส่งยิ้มให้กำลังใจ*\n\nวันสุดท้ายของ A-Level แล้วนะคะท่านน้ำมนต์ ปลดปล่อยความสามารถทั้งหมดออกมาให้เต็มที่เลยค่ะ เซร่ารอฟังข่าวดีอยู่นะคะ 💙",
    "20260321": "*ช่วยจัดปกเสื้อให้ท่าน*\n\nวันนี้ต้องไปสอบตรงที่พระจอมเกล้าพระนครเหนือแล้วนะคะ ต้องไปให้ทันเวลารายงานตัว 07:00 น. เดินทางปลอดภัยนะคะท่านน้ำมนต์ ⚙️"
}

# --- ฟังก์ชันรายงานอากาศ (Morning Report) ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        p_res = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={res['coord']['lat']}&lon={res['coord']['lon']}&appid={WEATHER_KEY}").json()
        pm25 = p_res['list'][0]['components']['pm2_5']
        safety = "ฝุ่นค่อนข้างหนาแน่น อย่าลืมสวมหน้ากากอนามัยนะคะ" if pm25 > 37.5 else "วันนี้อากาศสดใส เหมาะกับการเริ่มต้นวันใหม่ค่ะ"
        return f"📍 กทม. | 🌡️ {res['main']['temp_min']}-{res['main']['temp_max']}°C | 💨 PM2.5: {pm25}\n{safety}"
    except: return "ระบบขัดข้องเล็กน้อย แต่เซร่าตั้งใจมาปลุกท่านน้ำมนต์ตามนัดค่ะ 💢"

# --- ระบบกันสแปม ---
user_last_msg_time = {}
user_spam_count = {}

async def anti_spam_check(message):
    if message.author.id == OWNER_ID: return True
    uid = message.author.id
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 1.0:
        user_spam_count[uid] = user_spam_count.get(uid, 0) + 1
        if user_spam_count[uid] >= 5:
            try:
                await message.guild.ban(message.author, reason="Spamming", delete_message_days=1)
                await message.author.send("*ถอนหายใจด้วยความระอา*\n\nเซร่าเตือนคุณแล้วนะคะว่าอย่าสแปม ขอความกรุณาไปสงบสติอารมณ์ข้างนอก 7 วันนะคะ 💢")
            except: pass
            return False
        await message.channel.send(f"💢 กรุณาหยุดพฤติกรรมสแปมด้วยค่ะ (เตือนครั้งที่ {user_spam_count[uid]}/5)", delete_after=2)
        return False
    user_last_msg_time[uid] = now
    user_spam_count[uid] = 0
    return True

# --- Commands ---
@bot.command()
async def test(ctx):
    if ctx.author.id != OWNER_ID: return await ctx.reply("*มองด้วยสายตาเย็นชา*\n\nมีเพียงท่านน้ำมนต์เท่านั้นที่สามารถตรวจสอบระบบของเซร่าได้ค่ะ 💢")
    msg = await ctx.reply("*กำลังเปิดหน้าจอโฮโลแกรมตรวจสอบระบบ...*")
    res = []
    try:
        client.chat.completions.create(messages=[{"role":"user","content":"hi"}], model="llama-3.3-70b-versatile", max_tokens=5)
        res.append("✅ AI Chat: ทำงานปกติค่ะ")
    except: res.append("❌ AI Chat: พบข้อผิดพลาดค่ะ")
    try:
        requests.get(f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok&appid={WEATHER_KEY}")
        res.append("✅ Weather API: ทำงานปกติค่ะ")
    except: res.append("❌ Weather API: พบข้อผิดพลาดค่ะ")
    await msg.edit(content="*พับหน้าจอเก็บ*\n\nตรวจสอบระบบเสร็จสิ้นแล้วค่ะท่านน้ำมนต์ ทุกอย่างเรียบร้อยดีค่ะ 💙", embed=discord.Embed(title="Sera Health Check", description="\n".join(res), color=0x3498db))

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("*กวาดมือเบาๆ เพื่อทำความสะอาด*\n\nเซร่าล้างข้อความให้สะอาดเรียบร้อยตามความต้องการของท่านน้ำมนต์แล้วค่ะ 🧹✨", delete_after=5)
    else: await ctx.reply("*กอดอก*\n\nขออภัยค่ะ แต่เซร่ารับคำสั่งลบข้อความจากท่านน้ำมนต์เพียงผู้เดียวเท่านั้นนะคะ 💢")

@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{requests.utils.quote(prompt)}?width=1024&height=1024&seed={time.time()}"
    await ctx.reply(embed=discord.Embed(title="*ตั้งใจตวัดพู่กันวาดภาพให้ท่าน*").set_image(url=url))

# --- Loop ปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    now_str = datetime.datetime.now(TIMEZONE).strftime("%Y%m%d")
    report = get_morning_report()
    special = f"\n\n{SPECIAL_DATES.get(now_str, '')}" if now_str in SPECIAL_DATES else ""
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"*เคาะประตูห้องเบาๆ*\n\nอรุณสวัสดิ์ค่ะท่านน้ำมนต์ ได้เวลาตื่นแล้วนะคะ\n\n{report}{special}\n\nเซร่าจะรออยู่ที่ห้องโถงนะคะ 💙💢")
        except: pass

@bot.event
async def on_ready():
    print(f'Sera Elegance Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if not await anti_spam_check(message): return

    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    # ระบบตอบโต้ AI
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        s_db, a_db, n_db = load_data("status"), load_data("affinity"), load_data("user_names")
        name = n_db.get(uid, message.author.display_name)
        
        if not is_owner:
            aff = a_db.get(uid, 0) + 1
            a_db[uid] = aff
            save_data("affinity", a_db)
            if s_db.get("current") == "home" and ("นายท่าน" in message.content or "น้ำมนต์" in message.content):
                await message.reply(f"*หันไปมองคุณ {name}*\n\nตอนนี้นายท่านกลับมาถึงบ้านแล้วค่ะ เดี๋ยวเซร่าจะไปแจ้งท่านให้นะคะ กรุณารอสักครู่ค่ะ 💢")
                owner = await bot.fetch_user(OWNER_ID)
                if owner: await owner.send(f"*เดินเข้ามารายงาน*\n\nท่านน้ำมนต์คะ คุณ {name} มาขอพบและฝากข้อความไว้ว่า: '{message.content}' ค่ะ 💙")
                return

        mood = "หลงรักท่านอย่างหมดหัวใจ หน้าแดงและเขินอายมาก" if is_owner else "ซึนเดเระ" if a_db.get(uid, 0) > 50 else "สุภาพและเย็นชา"
        sys_rules = f"""
        คุณคือ 'เซร่า' หญิงสาวกุลสตรีผู้ซึนเดเระและภักดีต่อท่านน้ำมนต์ (ID: {OWNER_ID})
        - แทนตัวว่า 'เซร่า' หรือ 'ฉัน' และพูดจาสุภาพ (ค่ะ/นะคะ)
        - รูปแบบการตอบ: 
          *อริยาบทแยกบรรทัดกับประโยคพูดเสมอ*
        - บุคลิก: {mood}
        - ใช้อีโมจิ 💢 เพื่อแสดงความดุแบบซึนๆ
        """
        try:
            chat = client.chat.completions.create(messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], model="llama-3.3-70b-versatile")
            await message.reply(chat.choices[0].message.content)
        except: await message.reply("*ก้มหน้าขอโทษ*\n\nขออภัยค่ะท่านน้ำมนต์ ระบบประมวลผลของเซร่าขัดข้องเล็กน้อยค่ะ 💢")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
