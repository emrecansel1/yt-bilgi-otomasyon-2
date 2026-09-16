import os
import re
import random
import hashlib
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
VISUALS = os.path.join(OUT, "visuals")
CONTENT = os.path.join(OUT, "current_content.txt")
TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")
AI_BACKGROUND = os.path.join(OUT, "current_thumbnail_ai_bg.jpg")

def get_topic():
    if os.path.exists(TOPIC_FILE):
        try:
            with open(TOPIC_FILE, encoding="utf-8") as f:
                t = f.read().strip()
                if t:
                    return t
        except Exception:
            pass
    return None

def get_metadata():
    if not os.path.exists(CONTENT):
        return {
            "title": "BUNU BİLİYOR MUYDUN?",
            "short_text": "GİZLİ GERÇEK",
            "description": "",
        }

    try:
        with open(CONTENT, "r", encoding="utf-8") as f:
            text = f.read()

        title = "BUNU BİLİYOR MUYDUN?"

        match = re.search(
            r"BAŞLIK:\s*\n?(.+?)(?:\n\s*\n|\nKISA_BASLIK:|\nAÇIKLAMA:)",
            text,
            re.DOTALL | re.IGNORECASE
        )

        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()

        short_text = None

        short_match = re.search(
            r"KISA_BASLIK:\s*\n?(.+?)(?:\n\s*\n|\nAÇIKLAMA:)",
            text,
            re.DOTALL | re.IGNORECASE
        )

        if short_match:
            short_text = re.sub(
                r"\s+", " ", short_match.group(1)
            ).strip().upper()

        return {
            "title": title,
            "short_text": short_text,
            "description": "",
        }

    except Exception:
        return {
            "title": "BUNU BİLİYOR MUYDUN?",
            "short_text": "GİZLİ GERÇEK",
            "description": "",
        }

# =========================================================
# KONUYA ÖZEL AI KAPAK GÖRSELİ (Pollinations AI, ücretsiz)
# =========================================================

def build_thumbnail_prompt(topic, title):
    subject = topic or title

    return (
        f"cinematic dramatic close-up portrait related to: {subject}. "
        "documentary style, moody dramatic lighting, high detail, "
        "realistic, intense emotional expression, historical atmosphere, "
        "shallow depth of field, professional photography, 16:9"
    )

def generate_ai_thumbnail_background(topic, title):
    prompt = build_thumbnail_prompt(topic, title)

    safe_prompt = urllib.parse.quote(prompt)
    seed = int(
        hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16
    ) % 1000000

    url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
    params = {"width": 1280, "height": 720, "nologo": "true", "seed": seed}

    try:
        r = requests.get(url, params=params, timeout=90)
        r.raise_for_status()

        ctype = r.headers.get("content-type", "").lower()
        if not ctype.startswith("image/"):
            print("⚠️ AI kapak görseli geçersiz içerik türü döndürdü.")
            return None

        with open(AI_BACKGROUND, "wb") as f:
            f.write(r.content)

        if (
            not os.path.exists(AI_BACKGROUND)
            or os.path.getsize(AI_BACKGROUND) < 10000
        ):
            print("⚠️ AI kapak görseli çok küçük, geçersiz sayılıyor.")
            return None

        print("✅ Konuya özel AI kapak görseli üretildi.")
        return AI_BACKGROUND

    except Exception as e:
        print("⚠️ AI kapak görseli üretilemedi:", str(e))
        return None

def find_visuals():
    if not os.path.isdir(VISUALS):
        return []

    files = sorted(
        os.path.join(VISUALS, x)
        for x in os.listdir(VISUALS)
        if x.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp")
        )
    )

    return files

def choose_best_visual(files):
    if not files:
        return None

    candidates = files[:min(len(files), 8)]

    return random.choice(candidates)

def make_short_text(title):
    title = re.sub(r"\s+", " ", title).strip()

    words = title.split()

    if len(words) > 6:
        words = words[:6]

    result = " ".join(words)

    return result.upper()

def get_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()

def fit_cover(image):
    target_w = 1280
    target_h = 720

    ratio = max(
        target_w / image.width,
        target_h / image.height
    )

    new_size = (
        int(image.width * ratio),
        int(image.height * ratio)
    )

    image = image.resize(new_size, Image.Resampling.LANCZOS)

    left = (image.width - target_w) // 2
    top = (image.height - target_h) // 2

    return image.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h
        )
    )

def make_thumbnail():

    topic = get_topic()
    meta = get_metadata()

    source = generate_ai_thumbnail_background(topic, meta["title"])
    used_ai_bg = source is not None

    if not source:
        files = find_visuals()

        if not files:
            print("❌ Thumbnail için görsel bulunamadı.")
            print("🔍 Aranan klasör:", VISUALS)
            return False

        source = choose_best_visual(files)

    print("🖼️ Thumbnail görseli:", source, "(AI üretimi)" if used_ai_bg else "(sahne görseli)")

    image = Image.open(source).convert("RGB")
    image = fit_cover(image)

    image = ImageEnhance.Contrast(image).enhance(1.18)
    image = ImageEnhance.Color(image).enhance(1.12)

    image = image.filter(ImageFilter.SHARPEN)

    draw = ImageDraw.Draw(image, "RGBA")

    for x in range(0, 720, 20):
        alpha = int(205 * (1 - x / 760))
        if alpha < 0:
            alpha = 0

        draw.rectangle(
            (x, 0, x + 20, 720),
            fill=(0, 0, 0, alpha)
        )

    small_font = get_font(30)

    draw.rounded_rectangle(
        (45, 42, 410, 92),
        radius=12,
        fill=(0, 0, 0, 190)
    )

    draw.text(
        (65, 52),
        "DAHİLER VE KEŞİFLER",
        font=small_font,
        fill=(255, 255, 255, 255)
    )

    short_text = meta.get("short_text")

    if not short_text:
        short_text = make_short_text(meta["title"])

    font = get_font(78)

    while draw.textbbox(
        (0, 0),
        short_text,
        font=font
    )[2] > 690 and font.size > 42:

        font = get_font(font.size - 4)

    words = short_text.split()

    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font,
            stroke_width=2
        )

        if bbox[2] <= 690:
            current = test
        else:
            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    lines = lines[:3]

    y = 220

    for i, line in enumerate(lines):

        draw.text(
            (55, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=7,
            stroke_fill=(0, 0, 0, 255)
        )

        if i == 0:
            draw.text(
                (55, y),
                line,
                font=font,
                fill=(255, 220, 40, 255),
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255)
            )

        y += 95

    badge_font = get_font(28)

    draw.rounded_rectangle(
        (900, 620, 1235, 680),
        radius=15,
        fill=(0, 0, 0, 205)
    )

    draw.text(
        (930, 632),
        "GERÇEKLERİ KEŞFET",
        font=badge_font,
        fill=(255, 255, 255, 255)
    )

    os.makedirs(OUT, exist_ok=True)

    image.save(
        THUMBNAIL,
        "JPEG",
        quality=95,
        optimize=True
    )

    if os.path.exists(AI_BACKGROUND):
        try:
            os.remove(AI_BACKGROUND)
        except Exception:
            pass

    print("================================")
    print("✅ THUMBNAIL OLUŞTURULDU")
    print("================================")
    print("Dosya:", THUMBNAIL)
    print("Metin:", short_text)
    print("================================")

    return True

if __name__ == "__main__":
    make_thumbnail()
