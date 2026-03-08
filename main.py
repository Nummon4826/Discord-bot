import discord
import os
from google import genai
from discord.ext import commands

# --- การตั้งค่า API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client = genai.Client(api_key=GEMINI_API_KEY)

# --- การตั้งค่าบุคลิก ---
SYSTEM_PROMPT = """
คุณคือ AI สาวซึนเดเระ ชื่อ 'เซร่า'
ถ้าผู้ใช้คือ 'nummonrapeewit' หรือ 'nummon4826' ให้เรียกว่า "นายท่านน้ำมนต์" เท่านั้น
บุคลิก: เย็นชาแต่ใจดี พูดจาประชดประชันเล็กน้อย ตอบสั้นๆ มีคำว่า 'นะ...', 'เหอะ!'
"""

# --- การตั้งค่า Discord Bot ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        try:
            # ใช้โมเดล gemini-2.0-flash ล่าสุดไปเลยครับ
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                config={'system_instruction': SYSTEM_PROMPT},
                contents=f"User ({message.author.name}): {user_input}"
            )
            await message.reply(response.text)
        except Exception as e:
            print(f"Error: {e}")
            await message.reply("ชิ... ระบบขัดข้องนิดหน่อยน่ะ อย่ามาจ้องจับผิดกันสิ!")

bot.run(DISCORD_TOKEN)
