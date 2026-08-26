import os
import sys
import json
import requests
import re
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))

OUTPUT_FILE = os.path.join(BASE, "shorts_content.json")

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY bulunamadı.")

if len(sys.argv) < 2:
    raise RuntimeError(
        'Kullanım: python shorts_content.py "KONU"'
    )

TOPIC = " ".join(sys.argv[1:]).strip()


def clean_text(text):
    text = re.sub(r"\[[^\]]*\]", "", text or "")
    text = re.sub(r"\([^)]*\)", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate(topic):

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
bilgi YouTube kanalının Shorts içerik yazarısın.

KONU:
{topic}

GÖREV:

Bu konu hakkında 15-30 saniyede seslendirilebilecek,
kısa ve son derece çarpıcı bir YouTube Shorts
anlatım metni oluştur.

AMAÇ:

İzleyicinin daha ilk cümlede durup videoyu izlemeye
devam etmesini sağlamak. İzleyici hiçbir anda sıkılıp
kaydırmamalı.

ÇOK ÖNEMLİ:

- Bilgi uydurma, tarihi ve bilimsel gerçeklere sadık kal.
- Doğrulanamayan bilgiyi kesin gerçek gibi sunma.
- Gazete/haber dili kullanma, sıcak bir anlatıcı gibi konuş.
- Gereksiz detaya girme, sadece en çarpıcı 1-2 bilgiye odaklan.
- Konuyla alakasız hiçbir şey ekleme.
- Siyasi propaganda, hakaret veya kışkırtıcı dil kullanma.

KANAL TARZI:

- Türkçe.
- Doğal, akıcı, sıcak anlatıcı sesi.
- Kısa ve vurucu cümleler.
- İLK CÜMLE bir soru, şaşırtıcı bir gerçek veya çarpıcı bir
  iddia ile başlamalı ve izleyiciyi anında yakalamalı.
- "Merhaba arkadaşlar" gibi giriş yapma.
- Video ortasında hiç durgunluk olmasın, her cümle bir
  öncekinden daha meraklandırıcı olsun.
- SON CÜMLE izleyicide "bir daha izlemek" veya "bunu
  bilmiyordum, başkasına anlatmalıyım" hissi uyandırmalı;
  mümkünse videoyu tekrar baştan izlemek isteyecek şekilde
  ("loop-friendly") bir çarpıcı kapanışla bitsin.
- Kamera veya sahne açıklaması yazma.
- Müzik veya efekt yazma.
- Parantez içi açıklama yazma.

BAŞLIK:

- Özgün, merak uyandıran, ama yanıltıcı clickbait olmayan.
- Videoda anlatılmayan şeyi vaat etmemeli.
- Mümkünse önemli kişi, sayı veya sonucu içermeli.

METİN:

Yaklaşık 40-75 kelime yaz (15-30 saniyelik seslendirmeye
uygun uzunlukta). Bu bir üst sınır değil, hedef uzunluktur;
metni bu aralıkta tutmaya özen göster.

Metin sadece anlatıcının okuyacağı cümlelerden oluşsun.

AÇIKLAMA:

Videonun ne anlattığını 1-2 kısa cümleyle açıkla.

ETİKETLER:

8-12 adet alakalı Türkçe etiket yaz.
Virgülle ayır. Hashtag (#) kullanma.

ÇIKTIYI TAM OLARAK ŞU FORMATTA VER:

BAŞLIK:
...

METİN:
...

AÇIKLAMA:
...

ETİKETLER:
...
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.6-flash:generateContent"
    )

    response = requests.post(
        url,
        params={"key": API_KEY},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["candidates"][0]
        ["content"]["parts"][0]["text"]
    )


def parse(text, topic):

    text = clean_text(text)

    title = ""
    script = ""
    description = ""
    tags = ""

    match = re.search(
        r"BAŞLIK:\s*(.*?)(?=\s*METİN:)",
        text,
        re.I | re.S
    )

    if match:
        title = match.group(1).strip()

    match = re.search(
        r"METİN:\s*(.*?)(?=\s*AÇIKLAMA:)",
        text,
        re.I | re.S
    )

    if match:
        script = match.group(1).strip()

    match = re.search(
        r"AÇIKLAMA:\s*(.*?)(?=\s*ETİKETLER:)",
        text,
        re.I | re.S
    )

    if match:
        description = match.group(1).strip()

    match = re.search(
        r"ETİKETLER:\s*(.*)",
        text,
        re.I | re.S
    )

    if match:
        tags = match.group(1).strip()

    if not script:
        script = text

    words = len(script.split())

    if words < 30:
        print("[UYARI] Metin çok kısa:", words, "kelime")

    if words > 100:
        print("[UYARI] Metin çok uzun:", words, "kelime")

    return {
        "topic": topic,
        "title": title,
        "script": script,
        "description": description,
        "tags": tags,
        "word_count": words
    }


def main():

    print("=" * 60)
    print("          SHORTS İÇERİK MOTORU (SABİT KONU HAVUZU)")
    print("=" * 60)
    print("Konu:", TOPIC)

    try:
        raw = generate(TOPIC)
        parsed = parse(raw, TOPIC)

        print()
        print("✅ Hazır |", parsed["word_count"], "kelime")
        print("BAŞLIK:", parsed["title"])

    except Exception as e:
        print("❌ HATA:", e)
        raise SystemExit(1)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": 1,
        "contents": [parsed]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("SHORTS İÇERİĞİ TAMAMLANDI")
    print("=" * 60)
    print("Dosya:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
                  
