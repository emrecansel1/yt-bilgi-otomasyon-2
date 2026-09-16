import os
import json
import random
import re

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

TOKEN = "token.json"
VIDEO = os.path.join(OUT, "shorts_final.mp4")
META_FILE = os.path.join(OUT, "shorts_meta.json")
CONFIG = "config.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

EK_HASHTAG_HAVUZU = [
    "#tarih",
    "#bilim",
    "#tarihçi",
    "#bilinmeyenler",
    "#keşif",
    "#bilgi",
    "#gizemliolaylar",
    "#dünyatarihi",
    "#ilginçbilgiler",
    "#arkeoloji",
]

EK_HASHTAG_SAYISI = 3

def load_config():
    if not os.path.exists(CONFIG):
        return {}

    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_meta():
    if not os.path.exists(META_FILE):
        return {}

    try:
        with open(META_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def sanitize_tags(raw_tags):
    """YouTube API'nin reddetmemesi için etiketleri temizler:
    satır sonu/özel karakterleri kaldırır, uzunluk ve toplam
    boyut sınırlarına uydurur."""

    cleaned = []
    total_len = 0

    for t in raw_tags:
        tag = str(t).replace("\n", " ").replace("\r", " ")
        tag = tag.strip().strip("#").strip('"').strip("'").strip()
        tag = re.sub(r"\s+", " ", tag)
        tag = re.sub(r"[<>]", "", tag)

        if not tag:
            continue

        if len(tag) > 30:
            tag = tag[:30].strip()

        if not tag:
            continue

        added_len = len(tag) + 2

        if total_len + added_len > 460:
            break

        if tag.lower() not in [c.lower() for c in cleaned]:
            cleaned.append(tag)
            total_len += added_len

        if len(cleaned) >= 25:
            break

    return cleaned

def secili_ek_hashtagler():
    secim = random.sample(
        EK_HASHTAG_HAVUZU,
        min(EK_HASHTAG_SAYISI, len(EK_HASHTAG_HAVUZU))
    )
    return " ".join(secim)

def get_credentials():
    if not os.path.exists(TOKEN):
        raise SystemExit(
            "❌ token.json bulunamadı."
        )

    try:
        with open(TOKEN, encoding="utf-8") as f:
            token_data = json.load(f)

        creds = Credentials.from_authorized_user_info(
            token_data,
            SCOPES
        )

    except Exception as e:
        raise SystemExit(
            f"❌ token.json okunamadı: {e}"
        )

    if creds.valid:
        print("✅ YouTube token geçerli.")
        return creds

    if not creds.refresh_token:
        raise SystemExit(
            "❌ YouTube token geçersiz ve refresh token yok."
        )

    try:
        print("🔄 YouTube token yenileniyor...")
        creds.refresh(Request())

    except RefreshError as e:
        print()
        print("=" * 60)
        print("❌ YOUTUBE OAUTH TOKEN GEÇERSİZ")
        print("=" * 60)
        print("Yeni token.json oluşturup GitHub TOKEN_JSON secret'ını güncelle.")
        print("Hata:", e)
        print("=" * 60)
        raise SystemExit(1)

    try:
        with open(TOKEN, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print("✅ Token yenilendi.")

    except Exception as e:
        print("⚠️ Token kaydedilemedi:", e)

    return creds

def upload():
    print("=" * 40)
    print("📱 YOUTUBE SHORTS YÜKLEYİCİ")
    print("=" * 40)

    if not os.path.exists(VIDEO):
        raise SystemExit(
            f"❌ Video bulunamadı: {VIDEO}"
        )

    creds = get_credentials()

    youtube = build(
        "youtube",
        "v3",
        credentials=creds
    )

    config = load_config()
    youtube_config = config.get("youtube", {})
    meta = load_meta()

    title = meta.get("title", "").strip()

    if not title:
        title = "İlginç Bilgiler | Shorts"

    if "#shorts" not in title.lower():
        title = title[:90] + " #Shorts"

    description = meta.get("description", "").strip()

    if not description:
        description = "Bilim, tarih ve dünyadan ilginç bilgiler."

    ek_hashtagler = secili_ek_hashtagler()

    if "#shorts" not in description.lower():
        description += "\n\n#Shorts " + ek_hashtagler
    else:
        description += "\n\n" + ek_hashtagler

    raw_tags = meta.get("tags", "")

    if raw_tags:
        raw_list = [
            t.strip()
            for t in raw_tags.split(",")
            if t.strip()
        ]
        tags = sanitize_tags(raw_list)
    else:
        tags = [
            "bilgi",
            "bilim",
            "shorts"
        ]

    if "shorts" not in [t.lower() for t in tags]:
        tags.append("shorts")

    privacy = youtube_config.get(
        "privacy",
        "public"
    )

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": str(
                youtube_config.get(
                    "category_id",
                    "27"
                )
            ),
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr"
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        VIDEO,
        mimetype="video/mp4",
        resumable=True
    )

    print("📤 YouTube Shorts yükleniyor...")
    print("🎬 Başlık:", title)
    print("📁 Video:", VIDEO)
    print("📺 Format: 1080x1920 (dikey)")
    print()

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            print(
                f"📊 Yükleme: "
                f"{int(status.progress() * 100)}%"
            )

    video_id = response.get("id")

    if not video_id:
        raise SystemExit(
            "❌ YouTube video ID döndürmedi."
        )

    print()
    print("=" * 40)
    print("✅ YOUTUBE SHORTS YÜKLENDİ")
    print("=" * 40)
    print("🆔 Video ID:", video_id)
    print(
        "🔗 https://www.youtube.com/shorts/"
        + video_id
    )
    print("=" * 40)

    return video_id

if __name__ == "__main__":
    upload()
