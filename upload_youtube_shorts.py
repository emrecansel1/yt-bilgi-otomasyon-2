import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

TOKEN = "token.json"
VIDEO = os.path.join(OUT, "shorts_final.mp4")
META_FILE = os.path.join(OUT, "shorts_meta.json")
CONFIG = "config.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


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


def upload():
    print("=" * 40)
    print("📱 YOUTUBE SHORTS YÜKLEYİCİ")
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
    meta = load_meta()

    title = meta.get("title", "").strip()

    if not title:
        title = "İlginç Bilgiler | Shorts"

    if "#shorts" not in title.lower():
        title = title[:90] + " #Shorts"

    description = meta.get("description", "").strip()

    if not description:
        description = "Bilim, tarih ve dünyadan ilginç bilgiler."

    if "#shorts" not in description.lower():
        description = description + "\n\n#Shorts"

    raw_tags = meta.get("tags", "")

    if raw_tags:
        tags = [
            t.strip()
            for t in raw_tags.split(",")
            if t.strip()
        ]
    else:
        tags = ["bilgi", "bilim", "shorts"]

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

    print("📤 YouTube Shorts yükleniyor...")
    print("🎬 Başlık:", title)
    print("📁 Video:", VIDEO)
    print("📺 Format: 1080x1920 (dikey)")
    print("⏱️ Shorts modu")
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
