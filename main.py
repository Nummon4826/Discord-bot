import discord
import os
from groq import Groq
from discord.ext import commands

# ดึงค่าจาก Variables ใน Railway (เปลี่ยนชื่อตัวแปรเป็น GROQ_API_KEY ด้วยนะ)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
คุณคือ AI สาวซึนเดเระ ชื่อ 'เซร่า' 
ถ้าผู้ใช้คือ 'nummonrapeewit' หรือ 'nummon4826' ให้เรียกว่า "นายท่านน้ำมนต์" เท่านั้น
บุคลิก: เย็นชาแต่ใจดี พูดจาประชดประชันเล็กน้อย ตอบสั้นๆ มีคำว่า 'นะ...', 'เหอะ!'
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} — ย้ายค่ายมา Groq แล้วค่ะนายท่านน้ำมนต์!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        try:
            # ใช้โมเดล Llama 3 ของ Meta ผ่าน Groq
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                model="llama-3.3-70b-versatile",
            )
            await message.reply(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"Error: {e}")
            await message.reply("ชิ... ระบบขัดข้องอีกแล้วเหรอ? น่ารำคาญจริง!")

bot.run(DISCORD_TOKEN)
