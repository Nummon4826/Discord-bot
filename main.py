import discord
import os
from google import genai
from discord.ext import commands

# ดึงค่าจาก Variables ใน Railway
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ตั้งค่า Client ด้วย Library ตัวใหม่
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
คุณคือ AI สาวซึนเดเระ ชื่อ 'เซร่า'
ถ้าผู้ใช้คือ 'nummonrapeewit' หรือ 'nummon4826' ให้เรียกว่า "นายท่านน้ำมนต์" เท่านั้น
บุคลิก: ภายนอกเย็นชา พูดจาประชดประชันนิดๆ แต่จริงๆ ใจดี ตอบสั้นๆ มีคำว่า 'นะ...', 'เหอะ!'
"""

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # ข้อความนี้ยืนยันว่าบอทพร้อมทำงานแล้ว
    print(f'Logged in as {bot.user.name} — พร้อมรับใช้นายท่านน้ำมนต์แล้วค่ะ!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ตอบเมื่อโดน Tag
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        try:
            # ใช้โมเดล gemini-2.0-flash ล่าสุด
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                config={'system_instruction': SYSTEM_PROMPT},
                contents=user_input
            )
            await message.reply(response.text)
        except Exception as e:
            print(f"Error: {e}")
            await message.reply("ชิ... ระบบขัดข้องนิดหน่อยน่ะ อย่ามาจ้องจับผิดกันสิ!")

bot.run(DISCORD_TOKEN)
