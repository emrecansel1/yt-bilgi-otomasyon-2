import os
import re
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
VISUALS = os.path.join(OUT, "visuals")
CONTENT = os.path.join(OUT, "current_content.txt")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")


def get_title():
    if not os.path.exists(CONTENT):
        return "BUNU BİLİYOR MUYDUN?"

    try:
        with open(CONTENT, "r", encoding="utf-8") as f:
            text = f.read()

        match = re.search(
            r"BAŞLIK:\s*\n?(.+?)(?:\n\s*\n|\nAÇIKLAMA:)",
            text,
            re.DOTALL | re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

    except Exception:
        pass

    return "BUNU BİLİYOR MUYDUN?"


def find_visual():
    if not os.path.isdir(VISUALS):
        return None

    files = sorted(
        os.path.join(VISUALS, x)
        for x in os.listdir(VISUALS)
        if x.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )

    return files[0] if files else None


def make_thumbnail():
    source = find_visual()

    if not source:
        print("❌ Thumbnail için görsel bulunamadı.")
        return False

    image = Image.open(source).convert("RGB")
    image = image.resize((1280, 720))

    draw = ImageDraw.Draw(image, "RGBA")

    # Alt bölüme okunaklı koyu alan
    draw.rectangle(
        (0, 390, 1280, 720),
        fill=(0, 0, 0, 175)
    )

    title = get_title()

    # Çok uzun başlığı thumbnail'e uygun kısalt
    title = re.sub(r"\s+", " ", title).strip()

    if len(title) > 48:
        title = title[:48].rsplit(" ", 1)[0] + "..."

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    font = None

    for path in font_paths:
        if os.path.exists(path):
            font = ImageFont.truetype(path, 58)
            break

    if font is None:
        font = ImageFont.load_default()

    # Yazıyı satırlara böl
    words = title.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()

        if draw.textbbox((0, 0), test, font=font)[2] <= 1120:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    lines = lines[:3]

    y = 425

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        x = (1280 - width) // 2

        # Siyah gölge
        draw.text(
            (x + 5, y + 5),
            line,
            font=font,
            fill=(0, 0, 0, 230)
        )

        # Ana yazı
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255)
        )

        y += 75

    os.makedirs(OUT, exist_ok=True)
    image.save(
        THUMBNAIL,
        "JPEG",
        quality=95
    )

    print("✅ Thumbnail oluşturuldu:", THUMBNAIL)

    return True


if __name__ == "__main__":
    make_thumbnail()
