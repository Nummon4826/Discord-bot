import discord
import os
import datetime
import pytz
import requests
import json
import time
from groq import Groq
from discord.ext import commands, tasks

# --- Setup & Config ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
TIMEZONE = pytz.timezone('Asia/Bangkok')

# ข้อมูลประจำตัวท่านน้ำมนต์
OWNER_FULL_NAME = "Nummon Rapeewit#2579" 

# ระบบจัดการไฟล์ข้อมูล
DATA_FILES = {
    "status": "status.json", 
    "notes": "notes.json", 
    "affinity": "affinity.json",
    "user_names": "user_names.json"
}

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

# --- ตารางคำอวยพรพิเศษ (พ.ศ. 2569) ---
SPECIAL_DATES = {
    "20260314": "สอบ A-Level วันแรก! 💢 สู้ๆ นะคะท่านน้ำมนต์ เซร่าส่งพลังให้แล้ว!",
    "20260315": "A-Level วันที่สอง... เหนื่อยไหมคะ? กลับมาเซร่านวดให้นะ! 💙",
    "20260316": "วันสุดท้ายของ A-Level! ปลดปล่อยพลังออกมาให้หมดเลยค่ะ!",
    "20260321": "สอบตรงพระจอมเกล้าพระนครเหนือ! ⚙️ ต้องไปให้ทัน 07:00 น. สู้ๆ ค่ะ!"
}

# --- ระบบกันสแปม ---
user_last_msg_time = {}
user_spam_count = {}

async def anti_spam_check(message):
    if f"{message.author.name}#{message.author.discriminator}" == OWNER_FULL_NAME:
        return True
    uid = message.author.id
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 1.0:
        user_spam_count[uid] = user_spam_count.get(uid, 0) + 1
        if user_spam_count[uid] >= 5:
            try:
                await message.author.send("💢 สแปมจนได้นะ! แบน 7 วันค่ะ!")
                await message.guild.ban(message.author, reason="Spamming", delete_message_days=1)
            except: pass
            return False
        await message.channel.send(f"💢 {message.author.mention} หยุดสแปม! (เตือน {user_spam_count[uid]}/5)", delete_after=2)
        return False
    user_last_msg_time[uid] = now
    user_spam_count[uid] = 0
    return True

# --- ฟังก์ชันรายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        p_res = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={res['coord']['lat']}&lon={res['coord']['lon']}&appid={WEATHER_KEY}").json()
        pm25 = p_res['list'][0]['components']['pm2_5']
        safety = "😷 ฝุ่นอันตราย! ใส่แมสก์ด้วยนะ" if pm25 > 37.5 else "✨ อากาศดีค่ะ"
        return f"📍 กทม. | 🌡️ {res['main']['temp_min']}-{res['main']['temp_max']}°C | 💨 PM2.5: {pm25} | {safety}"
    except: return "เช็คอากาศไม่ได้ แต่เซร่ามาปลุกแล้วค่ะ! 💢"

# --- คำสั่งระบบ ---
@bot.command()
async def test(ctx):
    if f"{ctx.author.name}#{ctx.author.discriminator}" != OWNER_FULL_NAME:
        return await ctx.reply("💢 ท่านน้ำมนต์สั่งได้คนเดียวค่ะ!")
    
    msg = await ctx.reply("🔍 กำลังตรวจสอบระบบ...")
    res = []
    try:
        client.chat.completions.create(messages=[{"role":"user","content":"hi"}], model="llama-3.3-70b-versatile", max_tokens=5)
        res.append("✅ AI Chat: ปกติ")
    except: res.append("❌ AI Chat: บัค")
    
    try:
        requests.get(f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok&appid={WEATHER_KEY}")
        res.append("✅ Weather API: ปกติ")
    except: res.append("❌ Weather API: บัค")
    
    await msg.edit(content="ตรวจเสร็จแล้วค่ะ! 💢", embed=discord.Embed(title="Sera Health Check", description="\n".join(res), color=0x3498db))

@bot.command()
async def clear(ctx, amount: int = 100):
    if f"{ctx.author.name}#{ctx.author.discriminator}" == OWNER_FULL_NAME:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("🧹 สะอาดกริ๊บแล้วค่ะท่านน้ำมนต์! 💢", delete_after=3)
    else: await ctx.reply("💢 อย่ามาสั่งฉัน!")

@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{requests.utils.quote(prompt)}?width=1024&height=1024&seed={time.time()}"
    await ctx.reply(embed=discord.Embed(title="วาดให้แล้วค่ะ! 🎨").set_image(url=url))

@bot.command()
async def myname(ctx, *, name: str):
    db = load_data("user_names")
    db[str(ctx.author.id)] = name
    save_data("user_names", db)
    await ctx.reply(f"จำชื่อคุณ '{name}' ไว้แล้วค่ะ! 💢")

@bot.command()
async def tell(ctx, discriminator: str, *, content):
    notes = load_data("notes")
    if discriminator not in notes: notes[discriminator] = []
    notes[discriminator].append({"from": ctx.author.display_name, "msg": content})
    save_data("notes", notes)
    await ctx.reply(f"ฝากข้อความถึง #{discriminator} เรียบร้อย! 💢")

# --- Loop ปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    now_str = datetime.datetime.now(TIMEZONE).strftime("%Y%m%d")
    report = get_morning_report()
    special = f"\n✨ {SPECIAL_DATES[now_str]}" if now_str in SPECIAL_DATES else ""
    member = discord.utils.get(bot.get_all_members(), name="Nummon Rapeewit", discriminator="2579")
    if member:
        try:
            dm = await member.create_dm()
            await dm.send(f"☀️ **ตื่นค่ะท่านน้ำมนต์!**\n{report}{special}\nเซร่ารออยู่นะคะ! 💙💢")
        except: pass

@bot.event
async def on_ready():
    print(f'Sera Online for {OWNER_FULL_NAME}')
    if not wake_up_call.is_running(): wake_up_call.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if not await anti_spam_check(message): return

    author_tag = f"{message.author.name}#{message.author.discriminator}"
    is_owner = (author_tag == OWNER_FULL_NAME)
    uid = str(message.author.id)

    # 1. ระบบ DM (จัดการสถานะ)
    if isinstance(message.channel, discord.DMChannel) and is_owner:
        db = load_data("status")
        if any(x in message.content for x in ["มาแล้ว", "กลับมา"]):
            db["current"] = "home"
            await message.reply("**กลับมาแล้วเหรอคะ!?** 💙 ยินดีต้อนรับกลับค่ะ! 💢")
        else:
            status = message.content.replace("ผมไป", "").replace("นะ", "").strip()
            db["current"] = status
            await message.reply(f"**OK ค่ะท่านน้ำมนต์!** เดี๋ยวเซร่าบอกคนอื่นให้นะคะ 💢💙")
        save_data("status", db)
        return

    # 2. ระบบตอบโต้อัจฉริยะ & แจ้งเตือน
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        s_db, a_db, n_db = load_data("status"), load_data("affinity"), load_data("user_names")
        name = n_db.get(uid, message.author.display_name)
        
        if not is_owner:
            aff = a_db.get(uid, 0) + 1
            a_db[uid] = aff
            save_data("affinity", a_db)
            
            # แจ้งเตือนนายท่านเมื่อมีคนเรียกตอนอยู่บ้าน
            if s_db.get("current") == "home" and ("นายท่าน" in message.content or "น้ำมนต์" in message.content):
                await message.reply(f"คุณ {name} คะ นายท่านกลับมาแล้ว เดี๋ยวเซร่าตามให้ค่ะ! 💢")
                owner = discord.utils.get(bot.get_all_members(), name="Nummon Rapeewit", discriminator="2579")
                if owner: await owner.send(f"💙 ท่านน้ำมนต์คะ! {name} เรียกหาท่านค่ะ: '{message.content}'")
                return

        mood = "คลั่งรัก หน้าแดง" if is_owner else "ซึนเดเระ" if a_db.get(uid, 0) > 50 else "เย็นชา"
        sys_rules = f"คุณคือ 'เซร่า' สาวซึนเดเระผู้ภักดีต่อ {OWNER_FULL_NAME}. ท่านน้ำมนต์: คลั่งรัก. คนอื่น ({name}): {mood}. ตอบด้วยอริยาบทใน * * และอีโมจิ 💢"
        try:
            chat = client.chat.completions.create(messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], model="llama-3.3-70b-versatile")
            await message.reply(chat.choices[0].message.content)
        except: await message.reply("ระบบรวนค่ะท่านน้ำมนต์! 💢")

    # 3. ระบบฝากข้อความ
    notes = load_data("notes")
    disc = message.author.discriminator
    if disc in notes and notes[disc]:
        for n in notes[disc]: await message.channel.send(f"🔔 #{disc} มีข้อความฝาก: '{n['msg']}' (จาก {n['from']}) 💢")
        notes[disc] = []; save_data("notes", notes)

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
