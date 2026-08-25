import os
import json
import requests
import re
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))

TOPICS_FILE = os.path.join(BASE, "shorts_topics.json")
RESEARCH_FILE = os.path.join(BASE, "arastirma.json")
OUTPUT_FILE = os.path.join(BASE, "shorts_content.json")

API_KEY = os.environ.get("GEMINI_API_KEY")


def clean_text(text):
    text = re.sub(r"\[[^\]]*\]", "", text or "")
    text = re.sub(r"\([^)]*\)", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_research(topic):
    if not os.path.exists(RESEARCH_FILE):
        return None

    try:
        with open(
            RESEARCH_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            research = json.load(f)

    except Exception as e:
        print("[UYARI] Araştırma okunamadı:", e)
        return None

    research_topic = research.get(
        "topic",
        ""
    )

    topic_words = set(
        x.lower()
        for x in re.findall(
            r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+",
            topic
        )
        if len(x) >= 4
    )

    research_words = set(
        x.lower()
        for x in re.findall(
            r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+",
            research_topic
        )
        if len(x) >= 4
    )

    if topic_words and research_words:
        common = topic_words & research_words

        if len(common) == 0:
            print(
                "[UYARI] Araştırma mevcut konu ile uyuşmuyor."
            )
            return None

    return research


def research_context(research):
    if not research:
        return "Araştırma verisi bulunamadı."

    status = research.get(
        "verification",
        {}
    ).get(
        "status",
        "unknown"
    )

    source_count = research.get(
        "source_count",
        0
    )

    facts = research.get(
        "facts",
        []
    )

    lines = []

    lines.append(
        f"DOĞRULAMA DURUMU: {status}"
    )

    lines.append(
        f"İLGİLİ KAYNAK SAYISI: {source_count}"
    )

    lines.append("")
    lines.append("KAYNAKLAR:")

    for i, fact in enumerate(
        facts,
        1
    ):
        source = fact.get(
            "source",
            ""
        )

        title = fact.get(
            "title",
            ""
        )

        published = fact.get(
            "published",
            ""
        )

        lines.append(
            f"{i}. {source} | {title}"
        )

        if published:
            lines.append(
                f"   Tarih: {published}"
            )

    return "\n".join(lines)


def generate(topic, research):

    context = research_context(
        research
    )

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
bilgi YouTube kanalının Shorts içerik yazarısın.

ANA KONU:
{topic}

AŞAĞIDAKİ ARAŞTIRMA VERİLERİNİ KULLAN:

{context}

GÖREV:

Bu konu hakkında yaklaşık
40-55 saniyelik özgün bir YouTube Shorts
anlatım metni oluştur.

ÇOK ÖNEMLİ:

- Kaynak başlıklarını kopyalama.
- Haber metnini kopyalama.
- Gazete dilini taklit etme.
- Kaynaklarda olmayan bilgi uydurma.
- Bir bilgi yalnızca tek kaynakta varsa
  bunu kesin gerçek gibi sunma.
- Kaynaklar arasında çelişki varsa
  çelişkiyi gizleme.
- Araştırma verisinden çıkarılamayan
  ayrıntıları ekleme.
- Haberin kendisini değil,
  izleyicinin anlayacağı bilgi hikâyesini anlat.
- Güncel olaylarda taraf tutma.
- Siyasi propaganda yapma.
- Hakaret veya kışkırtıcı dil kullanma.

KANAL TARZI:

- Türkçe.
- Belgesel anlatımı.
- Doğal ve akıcı.
- Kısa cümleler.
- İlk cümle güçlü merak uyandırsın.
- Gereksiz giriş yapma.
- "Merhaba arkadaşlar" kullanma.
- Kamera veya sahne açıklaması yazma.
- Müzik veya efekt yazma.
- Parantez içi açıklama yazma.

BAŞLIK:

- Özgün olmalı.
- Haber başlığını aynen kullanma.
- Konuyla doğrudan alakalı olmalı.
- Merak uyandırmalı.
- Yanıltıcı clickbait olmamalı.
- Videoda anlatılmayan şeyi vaat etmemeli.
- Mümkünse önemli kişi, olay,
  sayı veya sonucu kullanmalı.

ÖRNEK:

Kötü:
"Trump'tan tarihi adım"

İyi:
"Suriye 47 Yıl Sonra Neden Listeden Çıkarıldı?"

Ancak örneği aynen kullanma.
Gerçek araştırma verisine göre kendi başlığını üret.

METİN:

Yaklaşık 90-130 kelime yaz.

Metin sadece anlatıcının okuyacağı
cümlelerden oluşsun.

AÇIKLAMA:

Videonun ne anlattığını 1-2 kısa
cümleyle açıkla.

ETİKETLER:

8-12 adet alakalı Türkçe etiket yaz.
Virgülle ayır.

Hashtag (#) kullanma.

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
        params={
            "key": API_KEY
        },
        json={
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return (
        data[
            "candidates"
        ][0][
            "content"
        ][
            "parts"
        ][0][
            "text"
        ]
    )


def parse(text, topic):

    text = clean_text(
        text
    )

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
        title = match.group(
            1
        ).strip()

    match = re.search(
        r"METİN:\s*(.*?)(?=\s*AÇIKLAMA:)",
        text,
        re.I | re.S
    )

    if match:
        script = match.group(
            1
        ).strip()

    match = re.search(
        r"AÇIKLAMA:\s*(.*?)(?=\s*ETİKETLER:)",
        text,
        re.I | re.S
    )

    if match:
        description = match.group(
            1
        ).strip()

    match = re.search(
        r"ETİKETLER:\s*(.*)",
        text,
        re.I | re.S
    )

    if match:
        tags = match.group(
            1
        ).strip()

    if not script:
        script = text

    words = len(
        script.split()
    )

    if words < 70:
        print(
            "[UYARI] Metin kısa:",
            words,
            "kelime"
        )

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
    print("          ARAŞTIRMALI SHORTS İÇERİK MOTORU")
    print("=" * 60)

    if not os.path.exists(
        TOPICS_FILE
    ):
        raise RuntimeError(
            "shorts_topics.json bulunamadı. "
            "Önce python shorts_brain.py çalıştır."
        )

    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    topics = data.get(
        "topics",
        []
    )

    if not topics:
        raise RuntimeError(
            "Hiç Shorts konusu bulunamadı."
        )

    contents = []

    for i, item in enumerate(
        topics,
        1
    ):

        topic = item.get(
            "topic",
            ""
        ).strip()

        if not topic:
            continue

        print()
        print(
            f"[{i}/{len(topics)}] Hazırlanıyor:"
        )
        print(topic)

        research = load_research(
            topic
        )

        if research:

            print(
                "🔎 Araştırma bulundu |",
                research.get(
                    "source_count",
                    0
                ),
                "kaynak |",
                research.get(
                    "verification",
                    {}
                ).get(
                    "status",
                    "unknown"
                )
            )

        else:

            print(
                "⚠️ Araştırma bulunamadı."
            )

        try:

            raw = generate(
                topic,
                research
            )

            parsed = parse(
                raw,
                topic
            )

            parsed["source"] = item.get(
                "source",
                ""
            )

            parsed["type"] = item.get(
                "type",
                ""
            )

            parsed["score"] = item.get(
                "score",
                ""
            )

            if research:

                parsed["research"] = {
                    "source_count":
                        research.get(
                            "source_count",
                            0
                        ),

                    "verification":
                        research.get(
                            "verification",
                            {}
                        ),

                    "sources":
                        research.get(
                            "sources",
                            []
                        )
                }

            contents.append(
                parsed
            )

            print(
                "✅ Hazır |",
                parsed["word_count"],
                "kelime"
            )

            print(
                "BAŞLIK:",
                parsed["title"]
            )

        except Exception as e:

            print(
                "❌ HATA:",
                e
            )

    result = {
        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(contents),

        "contents":
            contents
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("SHORTS İÇERİKLERİ TAMAMLANDI")
    print("=" * 60)

    print(
        "Üretilen içerik:",
        len(contents)
    )

    print(
        "Dosya:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
