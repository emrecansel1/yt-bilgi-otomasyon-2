import os
import random
import urllib.parse
import requests

# =========================================================
# ARKA PLAN MÜZİĞİ (TELİFSİZ - Kevin MacLeod / incompetech.com)
# Creative Commons By Attribution 4.0 lisanslı, ücretsiz.
# =========================================================

MUSIC_TRACKS = [
    "Wounded",
    "Long Note One",
    "Deadly Roulette",
    "Thinking Music",
    "Investigations",
    "Take a Chance",
    "Mystery Sax",
    "Curse of the Scarab",
    "The Cannery",
    "Marty Gots a Plan",
    "Constance",
    "Dark Times",
    "Killers",
    "Spellbound",
    "Crossing the Chasm",
    "Impact Moderato",
]

MUSIC_BASE_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"

MUSIC_CREDIT_TEMPLATE = (
    "\n\n---\n"
    "Müzik: \"{track}\" - Kevin MacLeod (incompetech.com)\n"
    "Lisans: Creative Commons By Attribution 4.0\n"
    "https://creativecommons.org/licenses/by/4.0/"
)

def pick_track():
    return random.choice(MUSIC_TRACKS)

def download_music(dest_path, track=None, timeout=30):

    track = track or pick_track()

    try:

        url = MUSIC_BASE_URL + urllib.parse.quote(track) + ".mp3"

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            f.write(response.content)

        if (
            not os.path.exists(dest_path)
            or os.path.getsize(dest_path) < 10000
        ):
            print(f"⚠️ Müzik dosyası geçersiz: {track}")
            return None

        print(f"🎵 Arka plan müziği indirildi: {track}")
        return track

    except Exception as e:

        print(f"⚠️ Müzik indirilemedi ({track}):", str(e))
        return None

def license_credit(track):
    return MUSIC_CREDIT_TEMPLATE.format(track=track)
