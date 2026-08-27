import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord.ext import commands, tasks
from flask import Flask

# ================= إعدادات الحدث (عدّل هنا فقط) =================
TIMEZONE = ZoneInfo("Asia/Riyadh")
EVENT_NAME = "حدث دورز"
# 2026/8/28 - الساعة 10:00 مساءً بتوقيت السعودية
TARGET_TIME = datetime(2026, 8, 28, 22, 0, 0, tzinfo=TIMEZONE)

TOKEN = os.environ.get("DISCORD_TOKEN")

# ================= سيرفر ويب بسيط (لأجل Render + UptimeRobot) =================
app = Flask("")

@app.route("/")
def home():
    return "البوت شغال ✅"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ================= إعداد البوت =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# نخزن هنا الرسالة الي نعدلها كل مرة بدل ما ننشئ رسالة جديدة كل تحديث
active_timers = {}  # channel_id -> discord.Message


def format_remaining(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"⏳ {days} يوم | {hours:02d} ساعة | {minutes:02d} دقيقة | {seconds:02d} ثانية"


def build_embed():
    """
    السر هنا: نحسب الوقت المتبقي من الآن (datetime.now) إلى موعد الحدث
    في كل مرة من الصفر. ما فيه عداد يتراكم عليه بطء أو خطأ أبدًا.
    """
    now = datetime.now(TIMEZONE)
    remaining = TARGET_TIME - now
    finished = remaining.total_seconds() <= 0

    if finished:
        embed = discord.Embed(
            title=f"🎉 {EVENT_NAME}",
            description="✅ **لقد بدأ الحدث الآن!**",
            color=discord.Color.green(),
        )
    else:
        embed = discord.Embed(
            title=f"⏰ العد التنازلي لـ {EVENT_NAME}",
            description=format_remaining(remaining),
            color=discord.Color.blurple(),
        )
        embed.set_footer(
            text=TARGET_TIME.strftime("موعد الحدث: %Y/%m/%d - %I:%M %p")
        )
    return embed, finished


@tasks.loop(seconds=5)
async def update_timers():
    # نحدث كل 5 ثواني (مو كل ثانية) عشان ما نصطدم بـ Rate Limit من ديسكورد
    # وهذا الي كان يسبب البطء عندك سابقًا
    to_remove = []
    for channel_id, message in active_timers.items():
        embed, finished = build_embed()
        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            to_remove.append(channel_id)
            continue
        except discord.HTTPException:
            # تجاهل أي خطأ مؤقت من الشبكة، بدون ما يأثر على دقة الوقت
            continue

        if finished:
            to_remove.append(channel_id)

    for cid in to_remove:
        active_timers.pop(cid, None)


@update_timers.before_loop
async def before_update_timers():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول باسم {bot.user}")
    if not update_timers.is_running():
        update_timers.start()


@bot.command(name="أبدأ")
async def start_timer(ctx):
    embed, finished = build_embed()
    msg = await ctx.send(embed=embed)
    if not finished:
        active_timers[ctx.channel.id] = msg


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        await message.channel.send(
            f"مرحباً {message.author.mention} 👋\n"
            f"اكتب `!أبدأ` لعرض العد التنازلي لـ {EVENT_NAME}."
        )

    await bot.process_commands(message)


# ================= تشغيل البوت =================
if __name__ == "__main__":
    keep_alive()
    if not TOKEN:
        raise RuntimeError("❌ لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة")
    bot.run(TOKEN)
