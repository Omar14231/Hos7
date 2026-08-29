import os
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord.ext import commands, tasks
from flask import Flask
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ================= إعدادات الحدث (عدّل هنا فقط) =================
TIMEZONE = ZoneInfo("Asia/Riyadh")
EVENT_NAME = "DOORS EVENT"
# 2026/8/28 - الساعة 10:00 مساءً بتوقيت السعودية
TARGET_TIME = datetime(2026, 8, 29, 21, 0, 0, tzinfo=TIMEZONE)

# الرتبة التي يتم منشنها عند بدء الحدث
ROLE_MENTION_ID = 1520078137902497922

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

# ================= إعداد الخطوط والألوان (تصميم الصورة) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")
FONT_REG_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")

W, H = 1400, 520
GOLD = (212, 175, 90)
GOLD_LIGHT = (238, 210, 140)
WHITE = (245, 245, 248)
BG_TOP = (8, 9, 14)
BG_BOTTOM = (18, 20, 30)


def vertical_gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_centered_text(draw, xy, text, font, fill, tracking=0):
    x, y = xy
    if tracking == 0:
        w = draw.textlength(text, font=font)
        draw.text((x - w / 2, y), text, font=font, fill=fill)
        return
    total_w = sum(draw.textlength(ch, font=font) + tracking for ch in text) - tracking
    cx = x - total_w / 2
    for ch in text:
        draw.text((cx, y), ch, font=font, fill=fill)
        cx += draw.textlength(ch, font=font) + tracking


def make_countdown_image(days, hours, minutes, seconds, finished=False):
    base = vertical_gradient((W, H), BG_TOP, BG_BOTTOM)

    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W / 2 - 500, -300, W / 2 + 500, 300), fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    gold_layer = Image.new("RGB", (W, H), GOLD)
    base = Image.composite(gold_layer, base, glow.point(lambda p: p // 6))

    draw = ImageDraw.Draw(base)

    draw.line([(W / 2 - 90, 46), (W / 2 + 90, 46)], fill=GOLD, width=2)

    title_font = ImageFont.truetype(FONT_BOLD_PATH, 30)
    draw_centered_text(draw, (W / 2, 62), EVENT_NAME.upper(), title_font, GOLD_LIGHT, tracking=10)

    subtitle_font = ImageFont.truetype(FONT_REG_PATH, 18)
    sub_text = "EVENT HAS STARTED" if finished else "COUNTDOWN TO LAUNCH"
    draw_centered_text(draw, (W / 2, 106), sub_text, subtitle_font, (150, 150, 160), tracking=6)

    if finished:
        big_font = ImageFont.truetype(FONT_BOLD_PATH, 130)
        draw_centered_text(draw, (W / 2, 220), "LIVE NOW", big_font, GOLD_LIGHT, tracking=4)
        base = base.filter(ImageFilter.SMOOTH)
        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf

    values = [(str(days).zfill(2), "DAYS"), (str(hours).zfill(2), "HOURS"),
              (str(minutes).zfill(2), "MINUTES"), (str(seconds).zfill(2), "SECONDS")]

    card_w, card_h = 280, 300
    gap = 30
    total_w = card_w * 4 + gap * 3
    start_x = (W - total_w) / 2
    top_y = 160

    num_font = ImageFont.truetype(FONT_BOLD_PATH, 130)
    label_font = ImageFont.truetype(FONT_BOLD_PATH, 20)

    for i, (val, label) in enumerate(values):
        x0 = start_x + i * (card_w + gap)
        x1 = x0 + card_w
        y0 = top_y
        y1 = y0 + card_h

        rounded_rect(draw, (x0, y0, x1, y1), 22, fill=(20, 21, 30))
        rounded_rect(draw, (x0, y0, x1, y1), 22, outline=(60, 55, 45), width=2)
        rounded_rect(draw, (x0 + 3, y0 + 3, x1 - 3, y1 - 3), 19, outline=(40, 38, 32), width=1)

        cx = x0 + card_w / 2
        draw_centered_text(draw, (cx, y0 + 55), val, num_font, WHITE)
        draw.line([(x0 + 60, y1 - 62), (x1 - 60, y1 - 62)], fill=GOLD, width=1)
        draw_centered_text(draw, (cx, y1 - 45), label, label_font, GOLD, tracking=6)

        if i < 3:
            colon_font = ImageFont.truetype(FONT_BOLD_PATH, 60)
            draw_centered_text(draw, (x1 + gap / 2, top_y + card_h / 2 - 40), ":", colon_font, GOLD)

    footer_font = ImageFont.truetype(FONT_REG_PATH, 16)
    draw_centered_text(draw, (W / 2, H - 40), "Doors — Next Update", footer_font, (110, 110, 120), tracking=4)

    base = base.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ================= إعداد البوت =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# channel_id -> {"message": discord.Message, "announced": bool}
active_timers = {}


def compute_remaining():
    """
    السر هنا: نحسب الوقت المتبقي من الآن (datetime.now) إلى موعد الحدث
    في كل مرة من الصفر. ما فيه عداد يتراكم عليه بطء أو خطأ أبدًا.
    """
    now = datetime.now(TIMEZONE)
    remaining = TARGET_TIME - now
    finished = remaining.total_seconds() <= 0
    if finished:
        return 0, 0, 0, 0, True

    total_seconds = int(remaining.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return days, hours, minutes, seconds, False


@tasks.loop(seconds=5)
async def update_timers():
    to_remove = []
    for channel_id, data in active_timers.items():
        message = data["message"]
        days, hours, minutes, seconds, finished = compute_remaining()
        buf = make_countdown_image(days, hours, minutes, seconds, finished)
        file = discord.File(fp=buf, filename="countdown.png")

        try:
            await message.edit(attachments=[file])
        except discord.NotFound:
            to_remove.append(channel_id)
            continue
        except discord.HTTPException:
            continue

        if finished and not data["announced"]:
            data["announced"] = True
            try:
                await message.channel.send(
                    f"<@&{ROLE_MENTION_ID}> 🎉 **{EVENT_NAME} بدأ الآن!**"
                )
            except discord.HTTPException:
                pass
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
    days, hours, minutes, seconds, finished = compute_remaining()
    buf = make_countdown_image(days, hours, minutes, seconds, finished)
    file = discord.File(fp=buf, filename="countdown.png")
    msg = await ctx.send(file=file)

    if not finished:
        active_timers[ctx.channel.id] = {"message": msg, "announced": False}
    else:
        await ctx.channel.send(f"<@&{ROLE_MENTION_ID}> 🎉 **{EVENT_NAME} بدأ الآن!**")


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
