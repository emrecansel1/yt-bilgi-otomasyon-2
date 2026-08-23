import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

TOKEN = os.path.join(BASE, "token.json")
VIDEO = os.path.join(OUT, "current_final.mp4")
CONFIG = os.path.join(BASE, "config.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def load_config():
    if not os.path.exists(CONFIG):
        return {}

    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def upload():
    print("=" * 40)
    print("📺 NORMAL YOUTUBE VİDEO YÜKLEYİCİ")
    print("=" * 40)

    if not os.path.exists(TOKEN):
        raise SystemExit("❌ token.json bulunamadı.")

    if not os.path.exists(VIDEO):
        raise SystemExit(f"❌ Video bulunamadı: {VIDEO}")

    with open(TOKEN, encoding="utf-8") as f:
        token_data = json.load(f)

    creds = Credentials.from_authorized_user_info(
        token_data,
        SCOPES
    )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            raise SystemExit("❌ YouTube token geçersiz veya yenilenemiyor.")

    youtube = build(
        "youtube",
        "v3",
        credentials=creds
    )

    config = load_config()

    youtube_config = config.get("youtube", {})

    title = config.get(
        "youtube_title",
        "İlginç Bilgiler | Bilim ve Tarih"
    )

    description = config.get(
        "youtube_description",
        "Bilim, tarih ve dünyadan ilginç bilgiler."
    )

    tags = config.get(
        "youtube_tags",
        ["bilgi", "bilim", "tarih", "ilginç bilgiler"]
    )

    privacy = youtube_config.get(
        "privacy",
        "public"
    )

    # NORMAL UZUN YOUTUBE VİDEOSU
    # Shorts'a özel hiçbir metadata kullanılmıyor.
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": str(
                youtube_config.get("category_id", "27")
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

    print("📤 Normal YouTube videosu yükleniyor...")
    print("🎬 Başlık:", title)
    print("📁 Video:", VIDEO)
    print("📺 Format: 1920x1080")
    print("⏱️ Uzun video modu")
    print("🔞 Shorts metadata: YOK")
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
    print("✅ NORMAL YOUTUBE VİDEOSU YÜKLENDİ")
    print("=" * 40)
    print("🆔 Video ID:", video_id)
    print(
        "🔗 https://www.youtube.com/watch?v="
        + video_id
    )
    print("=" * 40)

    return video_id


if __name__ == "__main__":
    upload()
