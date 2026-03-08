import discord
import os
import google.generativeai as genai
from discord.ext import commands

# --- การตั้งค่า API ---
GEN_AI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

genai.configure(api_key=GEN_AI_KEY)

# --- การตั้งค่าบุคลิก (System Instruction) ---
SYSTEM_PROMPT = """
คุณคือ AI สาวซึนเดเระ (Tsundere) ชื่อ 'เซร่า' 
บุคลิก: ภายนอกดูเย็นชา พูดจาประชดประชันเล็กน้อย แต่จริงๆ แล้วใจดีและเป็นห่วง
เงื่อนไขการเรียกชื่อ: 
- ถ้าผู้ใช้คือ 'nummonrapeewit' หรือ 'nummon4826' ให้เรียกว่า "นายท่านน้ำมนต์" เท่านั้น
- กับคนอื่นให้เรียก "ตาสว่าง" หรือ "คุณ" แบบห่างเหิน
หน้าที่: เป็นเพื่อนคุยแก้เหงา เรียนรู้และเก็บข้อมูลจากบทสนทนา (จำลองการจำ)
สไตล์การตอบ: สั้น กระชับ มีคำสร้อยเช่น 'นะ...', 'เหอะ!', 'ไม่ได้อยากตอบหรอกนะ!'
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# --- การตั้งค่า Discord Bot ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_message(message):
    # ไม่ตอบข้อความจากตัวเอง
    if message.author == bot.user:
        return

    # ตอบเมื่อโดน Tag หรือเป็น DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        
        # คลีนข้อความ (เอา Tag ออก)
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if not user_input:
            user_input = "อยู่ไหม?"

        try:
            # ส่งข้อความไปให้ Gemini
            response = model.generate_content(f"User ({message.author.name}): {user_input}")
            
            # ตอบกลับใน Discord
            await message.reply(response.text)
            
        except Exception as e:
            await message.channel.send("ชิ... เกิดข้อผิดพลาดนิดหน่อยน่ะ อย่าจ้องนักสิ!")
            print(e)

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
