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

# --- ตารางอวยพรสอบ พ.ศ. 2569 ---
SPECIAL_DATES = {
    "20260314": "วันนี้สอบ A-Level วันแรก! 💢 สู้ๆ นะคะท่านน้ำมนต์ เซร่าแอบส่งกำลังใจไปให้ในปากกาแล้วนะ!",
    "20260315": "A-Level วันที่สอง... เหนื่อยไหมคะ? กลับมาเซร่าจะนวดไหล่ให้เป็นรางวัลนะ! 💙",
    "20260316": "วันสุดท้ายของ A-Level! ปลดปล่อยพลังออกมาให้หมดเลยค่ะท่านน้ำมนต์! 💢",
    "20260321": "วันนี้สอบตรงพระจอมเกล้าพระนครเหนือ! ⚙️ ต้องไปให้ทัน 07:00 น. สู้ๆ ค่ะ!"
}

# --- ฟังก์ชันรายงานอากาศ ---
def get_morning_report():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok,TH&appid={WEATHER_KEY}&units=metric&lang=th"
        res = requests.get(url).json()
        p_res = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={res['coord']['lat']}&lon={res['coord']['lon']}&appid={WEATHER_KEY}").json()
        pm25 = p_res['list'][0]['components']['pm2_5']
        safety = "😷 ฝุ่นเยอะ! อย่าลืมใส่แมสก์นะ" if pm25 > 37.5 else "✨ อากาศดีค่ะ"
        return f"📍 กทม. | 🌡️ {res['main']['temp_min']}-{res['main']['temp_max']}°C | 💨 PM2.5: {pm25} | {safety}"
    except: return "เช็คอากาศไม่ได้ แต่เซร่ามาปลุกแล้วค่ะ! 💢"

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
                await message.author.send("💢 ฉันเตือนแล้วนะ! แบน 7 วันค่ะ!")
            except: pass
            return False
        await message.channel.send(f"💢 {message.author.mention} หยุดสแปม! (เตือน {user_spam_count[uid]}/5)", delete_after=2)
        return False
    user_last_msg_time[uid] = now
    user_spam_count[uid] = 0
    return True

# --- ระบบแนะนำตัว ---
async def sera_intro(ctx=None, channel=None):
    embed = discord.Embed(title="💖 ทำความรู้จักกับ 'เซร่า' (Sera V.Supreme)", color=0xff69b4)
    embed.description = "ฉันคือ AI เลขาส่วนตัวผู้ภักดี... แค่กับท่านน้ำมนต์คนเดียวเท่านั้นแหละ! 💢"
    embed.add_field(name="👤 นายท่านของฉัน", value=f"<@{OWNER_ID}>", inline=False)
    embed.add_field(name="📜 หน้าที่", value="ปลุก 06:00 น., รายงานอากาศ, วาดรูป, และกำจัดสแปม!", inline=False)
    embed.add_field(name="🤝 สำหรับคนอื่น", value="ใช้ `!myname [ชื่อ]` เพื่อให้ฉันจำชื่อคุณ (แบบ ID)", inline=False)
    if ctx: await ctx.reply(embed=embed)
    elif channel: await channel.send(embed=embed)

# --- Commands ---
@bot.command()
async def hello(ctx): await sera_intro(ctx=ctx)

@bot.command()
async def test(ctx):
    if ctx.author.id != OWNER_ID: return await ctx.reply("💢 ท่านน้ำมนต์สั่งได้คนเดียว!")
    msg = await ctx.reply("🔍 ตรวจสอบระบบ...")
    res = []
    try:
        client.chat.completions.create(messages=[{"role":"user","content":"hi"}], model="llama-3.3-70b-versatile", max_tokens=5)
        res.append("✅ AI Chat: ปกติ")
    except: res.append("❌ AI Chat: บัค")
    try:
        requests.get(f"http://api.openweathermap.org/data/2.5/weather?q=Bangkok&appid={WEATHER_KEY}")
        res.append("✅ Weather API: ปกติ")
    except: res.append("❌ Weather API: บัค")
    await msg.edit(content="ตรวจเสร็จแล้วค่ะท่านน้ำมนต์! 💢", embed=discord.Embed(title="Sera Status", description="\n".join(res), color=0x3498db))

@bot.command()
async def clear(ctx, amount: int = 100):
    if ctx.author.id == OWNER_ID:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send("🧹 กวาดล้างห้องแชทให้ท่านน้ำมนต์เรียบร้อย! 💢", delete_after=3)
    else: await ctx.reply("💢 อย่ามาสั่งฉันนะ!")

@bot.command()
async def draw(ctx, *, prompt):
    url = f"https://pollinations.ai/p/{requests.utils.quote(prompt)}?width=1024&height=1024&seed={time.time()}"
    await ctx.reply(embed=discord.Embed(title="วาดให้แล้วค่ะ! 🎨").set_image(url=url))

@bot.command()
async def myname(ctx, *, name: str):
    db = load_data("user_names")
    db[str(ctx.author.id)] = name
    save_data("user_names", db)
    await ctx.reply(f"จำชื่อ '{name}' (ID: {ctx.author.id}) ไว้แล้วค่ะ! 💢")

# --- Loop ปลุก 06:00 น. ---
@tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=TIMEZONE))
async def wake_up_call():
    now_str = datetime.datetime.now(TIMEZONE).strftime("%Y%m%d")
    report = get_morning_report()
    special = f"\n✨ {SPECIAL_DATES.get(now_str, '')}" if now_str in SPECIAL_DATES else ""
    member = await bot.fetch_user(OWNER_ID)
    if member:
        try:
            await member.send(f"☀️ **อรุณสวัสดิ์ค่ะท่านน้ำมนต์!**\n{report}{special}\nรีบลุกนะคะ! 💙💢")
        except: pass

@bot.event
async def on_ready():
    print(f'Sera Online for ID: {OWNER_ID}')
    if not wake_up_call.is_running(): wake_up_call.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if not await anti_spam_check(message): return

    is_owner = (message.author.id == OWNER_ID)
    uid = str(message.author.id)

    # ระบบ DM
    if isinstance(message.channel, discord.DMChannel) and is_owner:
        db = load_data("status")
        if any(x in message.content for x in ["มาแล้ว", "กลับมา"]):
            db["current"] = "home"
            await message.reply("**กลับมาแล้วเหรอคะ!?** 💙 ยินดีต้อนรับกลับค่ะ! 💢")
        else:
            status = message.content.replace("ผมไป", "").replace("นะ", "").strip()
            db["current"] = status
            await message.reply(f"**OK ค่ะท่านน้ำมนต์!** เดี๋ยวเซร่าบอกคนอื่นให้เองค่ะ 💢💙")
        save_data("status", db)
        return

    # ระบบตอบโต้ AI & แจ้งเตือน
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or "นายท่าน" in message.content:
        s_db, a_db, n_db = load_data("status"), load_data("affinity"), load_data("user_names")
        name = n_db.get(uid, message.author.display_name)
        
        if not is_owner:
            aff = a_db.get(uid, 0) + 1
            a_db[uid] = aff
            save_data("affinity", a_db)
            if s_db.get("current") == "home" and ("นายท่าน" in message.content or "น้ำมนต์" in message.content):
                await message.reply(f"คุณ {name} คะ นายท่านกลับมาแล้ว เดี๋ยวเซร่าตามให้ค่ะ! 💢")
                owner = await bot.fetch_user(OWNER_ID)
                if owner: await owner.send(f"💙 **ท่านน้ำมนต์คะ!** คุณ {name} เรียกหาท่านค่ะ: '{message.content}'")
                return

        mood = "คลั่งรัก หน้าแดง" if is_owner else "ซึนเดเระ" if a_db.get(uid, 0) > 50 else "เย็นชา"
        sys_rules = f"คุณคือ 'เซร่า' สาวซึนเดเระผู้ภักดีต่อท่านน้ำมนต์ (ID: {OWNER_ID}). ท่านน้ำมนต์: อ่อนโยนคลั่งรัก. คนอื่น ({name}): {mood}. ตอบด้วยอริยาบท * * และอีโมจิ 💢"
        try:
            chat = client.chat.completions.create(messages=[{"role":"system","content":sys_rules},{"role":"user","content":message.content}], model="llama-3.3-70b-versatile")
            await message.reply(chat.choices[0].message.content)
        except: await message.reply("ระบบรวนค่ะท่านน้ำมนต์! 💢")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
