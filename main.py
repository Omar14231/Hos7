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
EVENT_NAME = "TEAM TOURNAMENT"
# موعد بدء التختيم
TARGET_TIME = datetime(2026, 8, 29, 21, 0, 0, tzinfo=TIMEZONE)

# الرتبة التي يتم منشنها عند بدء الحدث
ROLE_MENTION_ID = 1543123745147986010

# الروم الي ينضم فيه الي يبي يدخل الفريق
JOIN_CHANNEL_LINK = "https://discord.com/channels/1474476686262145146/1540675111273635870"

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

# ================= إعداد الخطوط والألوان (تصميم الصورة - ثيم تختيم/بطولة) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")
FONT_REG_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")

W, H = 1400, 560

# ثيم بطولة/تختيم: أحمر ناري + أسود + لمسة ذهبية
RED = (214, 40, 57)
RED_LIGHT = (255, 92, 92)
GOLD = (240, 180, 80)
WHITE = (248, 248, 250)
BG_TOP = (10, 6, 8)
BG_BOTTOM = (26, 10, 14)
CARD_BG = (18, 10, 12)
CARD_BORDER = (90, 30, 30)


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


def draw_diagonal_stripes(base, y0, y1, color, alpha=26, gap=46):
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    w, h = base.size
    x = -h
    while x < w + h:
        od.line([(x, y1), (x + (y1 - y0), y0)], fill=color + (alpha,), width=10)
        x += gap
    base_rgba = base.convert("RGBA")
    base_rgba.alpha_composite(overlay)
    return base_rgba.convert("RGB")


def make_countdown_image(days, hours, minutes, seconds, finished=False):
    base = vertical_gradient((W, H), BG_TOP, BG_BOTTOM)

    # توهج أحمر خلف العنوان (بدل الذهبي القديم)
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W / 2 - 520, -320, W / 2 + 520, 280), fill=100)
    glow = glow.filter(ImageFilter.GaussianBlur(130))
    red_layer = Image.new("RGB", (W, H), RED)
    base = Image.composite(red_layer, base, glow.point(lambda p: p // 6))

    # خطوط قطرية خفيفة تعطي طابع بطولة/رياضي
    base = draw_diagonal_stripes(base, 0, H, RED)

    draw = ImageDraw.Draw(base)

    # شريط علوي مزدوج بدل الخط البسيط
    draw.line([(W / 2 - 130, 40), (W / 2 + 130, 40)], fill=GOLD, width=3)
    draw.line([(W / 2 - 60, 48), (W / 2 + 60, 48)], fill=RED_LIGHT, width=2)

    title_font = ImageFont.truetype(FONT_BOLD_PATH, 34)
    draw_centered_text(draw, (W / 2, 62), EVENT_NAME.upper(), title_font, WHITE, tracking=12)

    subtitle_font = ImageFont.truetype(FONT_REG_PATH, 18)
    sub_text = "TOURNAMENT IS LIVE" if finished else "COUNTDOWN TO KICKOFF"
    draw_centered_text(draw, (W / 2, 110), sub_text, subtitle_font, GOLD, tracking=6)

    if finished:
        big_font = ImageFont.truetype(FONT_BOLD_PATH, 120)
        draw_centered_text(draw, (W / 2, 230), "LIVE NOW", big_font, RED_LIGHT, tracking=4)

        join_font = ImageFont.truetype(FONT_REG_PATH, 22)
        draw_centered_text(draw, (W / 2, 380), "انضم للفريق الآن في روم التختيم", join_font, WHITE, tracking=2)

        base = base.filter(ImageFilter.SMOOTH)
        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf

    values = [(str(days).zfill(2), "DAYS"), (str(hours).zfill(2), "HOURS"),
              (str(minutes).zfill(2), "MINUTES"), (str(seconds).zfill(2), "SECONDS")]

    card_w, card_h = 280, 310
    gap = 30
    total_w = card_w * 4 + gap * 3
    start_x = (W - total_w) / 2
    top_y = 175

    num_font = ImageFont.truetype(FONT_BOLD_PATH, 130)
    label_font = ImageFont.truetype(FONT_BOLD_PATH, 20)

    for i, (val, label) in enumerate(values):
        x0 = start_x + i * (card_w + gap)
        x1 = x0 + card_w
        y0 = top_y
        y1 = y0 + card_h

        rounded_rect(draw, (x0, y0, x1, y1), 24, fill=CARD_BG)
        rounded_rect(draw, (x0, y0, x1, y1), 24, outline=RED, width=2)
        rounded_rect(draw, (x0 + 4, y0 + 4, x1 - 4, y1 - 4), 20, outline=CARD_BORDER, width=1)

        # زاوية علوية ذهبية صغيرة (طابع ميدالية/بطولة)
        draw.line([(x0 + 20, y0 + 14), (x0 + 70, y0 + 14)], fill=GOLD, width=3)
        draw.line([(x1 - 70, y0 + 14), (x1 - 20, y0 + 14)], fill=GOLD, width=3)

        cx = x0 + card_w / 2
        draw_centered_text(draw, (cx, y0 + 60), val, num_font, WHITE)
        draw.line([(x0 + 60, y1 - 64), (x1 - 60, y1 - 64)], fill=RED_LIGHT, width=1)
        draw_centered_text(draw, (cx, y1 - 46), label, label_font, GOLD, tracking=6)

        if i < 3:
            colon_font = ImageFont.truetype(FONT_BOLD_PATH, 60)
            draw_centered_text(draw, (x1 + gap / 2, top_y + card_h / 2 - 40), ":", colon_font, RED_LIGHT)

    footer_font = ImageFont.truetype(FONT_REG_PATH, 16)
    draw_centered_text(draw, (W / 2, H - 42), "TEAM TOURNAMENT — Next Update", footer_font, (140, 100, 100), tracking=4)

    base = base.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf


def finished_announcement():
    return (
        f"<@&{ROLE_MENTION_ID}> 🏆 **{EVENT_NAME} بدأ الآن!**\n"
        f"يلي يبي يدخل الفريق يدخل هنا 👇\n{JOIN_CHANNEL_LINK}"
    )


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
                await message.channel.send(finished_announcement())
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
        await ctx.channel.send(finished_announcement())


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
