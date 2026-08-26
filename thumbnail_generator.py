import os
import re
import random
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
VISUALS = os.path.join(OUT, "visuals")
CONTENT = os.path.join(OUT, "current_content.txt")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")


def get_metadata():
    if not os.path.exists(CONTENT):
        return {
            "title": "BUNU BİLİYOR MUYDUN?",
            "description": "",
        }

    try:
        with open(CONTENT, "r", encoding="utf-8") as f:
            text = f.read()

        title = "BUNU BİLİYOR MUYDUN?"

        match = re.search(
            r"BAŞLIK:\s*\n?(.+?)(?:\n\s*\n|\nAÇIKLAMA:)",
            text,
            re.DOTALL | re.IGNORECASE
        )

        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()

        return {
            "title": title,
            "description": "",
        }

    except Exception:
        return {
            "title": "BUNU BİLİYOR MUYDUN?",
            "description": "",
        }


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

    replacements = {
        "Okyanusların Keşfedilmemiş Gizemleri": "OKYANUSLARIN GİZEMİ",
        "Antik Mısır'ın Çözülemeyen Gizemleri": "MISIR'IN ÇÖZÜLEMEYEN SIRRI",
        "Albert Einstein'ın Hayatındaki En Şaşırtıcı Olaylar": "EINSTEIN'IN GİZLİ HİKÂYESİ",
        "Nikola Tesla'nın En Şaşırtıcı İcatları": "TESLA'NIN SIRRI",
        "İnsan Beyninin Bilinmeyen Özellikleri": "BEYNİMİZİN GİZLİ GÜCÜ",
    }

    for key, value in replacements.items():
        if key.lower() in title.lower():
            return value

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

    files = find_visuals()

    if not files:
        print("❌ Thumbnail için görsel bulunamadı.")
        print("🔍 Aranan klasör:", VISUALS)
        return False

    source = choose_best_visual(files)

    print("🖼️ Thumbnail görseli:", source)

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

    title = get_metadata()["title"]
    short_text = make_short_text(title)

    font = get_font(72)

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

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font,
            stroke_width=3
        )

        width = bbox[2] - bbox[0]

        x = 55

        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=7,
            stroke_fill=(0, 0, 0, 255)
        )

        if i == 0:
            draw.text(
                (x, y),
                line,
                font=font,
                fill=(255, 220, 40, 255),
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255)
            )

        y += 90

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

    print("================================")
    print("✅ THUMBNAIL OLUŞTURULDU")
    print("================================")
    print("Dosya:", THUMBNAIL)
    print("Metin:", short_text)
    print("================================")

    return True


if __name__ == "__main__":
    make_thumbnail()
            
