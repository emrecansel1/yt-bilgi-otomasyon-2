import os
import sys
import json
import re
import time
import random
import requests

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# GEMINI AYARLARI
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY bulunamadı.")
    raise SystemExit(1)

print("================================")
print("✅ GEMINI_API_KEY mevcut.")
print("🧠 Gemini model:", GEMINI_MODEL)
print("================================")

# =========================================================
# DOSYALAR
# =========================================================

TOPIC_FILE = os.path.join(
    OUT,
    "current_topic.txt"
)

TOPIC_HISTORY_FILE = os.path.join(
    REPO_BASE,
    "video_topic_history.json"
)

OUTPUT_FILE = os.path.join(
    OUT,
    "current_content.txt"
)

# =========================================================
# BELGESEL AYARLARI
# =========================================================

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# =========================================================
# KONU ÖRNEKLERİ
# =========================================================

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden dışlanması
- Nikola Tesla'nın son yılları ve yalnızlığı
- Alan Turing'in savaş dönemindeki çalışmaları ve gördüğü haksızlık
- Rosalind Franklin'in DNA araştırmalarındaki rolü
- Marie Curie'nin radyasyon araştırmaları
- Ludwig Boltzmann'ın bilim dünyasında yaşadığı mücadele
- Barbara McClintock'un keşfinin yıllarca kabul edilmemesi
- Galileo'nun bilimsel fikirleri nedeniyle yargılanması
- Évariste Galois'nın kısa ve trajik hayatı
- Vera Rubin'in karanlık madde araştırmaları
- Jocelyn Bell Burnell'in pulsar keşfi
- Emmy Noether'in akademik hayatta karşılaştığı engeller
- Ada Lovelace'in matematik ve bilgisayar tarihindeki yeri
- Katherine Johnson'un NASA'daki bilimsel çalışmaları
- Srinivasa Ramanujan'ın olağanüstü matematik hayatı
- Antoine Lavoisier'in bilimsel çalışmaları ve trajik sonu
"""

# =========================================================
# ANLATIM KURALLARI
# =========================================================

NARRATION_KURALLARI = """
1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Emin olunmayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı ve kronolojik şekilde anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Metin doğrudan TTS sistemine gönderilecek.
10. Sadece anlatım metni üret.
11. Sahne açıklaması yazma.
12. Kamera hareketi yazma.
13. Müzik veya ses efekti yazma.
14. Parantez kullanma.
15. Köşeli parantez kullanma.
16. "Sahne 1" gibi ifadeler kullanma.
17. "Bölüm 1" gibi ifadeler kullanma.
18. Metin kesintisiz bir belgesel anlatımı gibi ilerlemeli.
19. Uydurma diyalog oluşturma.
20. Uydurma alıntı oluşturma.
21. Gerçek dışı dramatizasyon yapma.
22. Kişinin insani tarafını doğal biçimde hissettir.
"""

# =========================================================
# GEMINI İSTEĞİ
# =========================================================

def call_gemini(prompt, max_retries=5):

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7
        }
    }

    for attempt in range(1, max_retries + 1):

        print(
            f"🤖 Gemini isteği {attempt}/{max_retries}"
        )

        try:

            response = requests.post(
                GEMINI_URL,
                params={
                    "key": GEMINI_API_KEY
                },
                headers=headers,
                json=payload,
                timeout=180
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            # =================================================
            # BAŞARILI
            # =================================================

            if response.status_code == 200:

                try:

                    data = response.json()

                    candidates = data.get(
                        "candidates",
                        []
                    )

                    if not candidates:
                        print(
                            "❌ Gemini candidates döndürmedi."
                        )
                        return None

                    content = candidates[0].get(
                        "content",
                        {}
                    )

                    parts = content.get(
                        "parts",
                        []
                    )

                    if not parts:
                        print(
                            "❌ Gemini parts döndürmedi."
                        )
                        return None

                    text = parts[0].get(
                        "text",
                        ""
                    )

                    if text.strip():

                        print(
                            "✅ Gemini cevap verdi."
                        )

                        return text.strip()

                    print(
                        "❌ Gemini boş cevap verdi."
                    )
                    return None

                except Exception as e:

                    print(
                        "❌ Gemini cevap okunamadı:",
                        str(e)
                    )

                    print(
                        response.text[:3000]
                    )

                    return None

            # =================================================
            # 429 KOTA
            # =================================================

            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429: kota veya hız limiti."
                )

                try:

                    error_data = response.json()

                    print(
                        json.dumps(
                            error_data,
                            ensure_ascii=False,
                            indent=2
                        )[:4000]
                    )

                except Exception:

                    print(
                        response.text[:4000]
                    )

                if attempt < max_retries:

                    wait_time = min(
                        60,
                        (
                            8 * (2 ** (attempt - 1))
                            + random.randint(1, 5)
                        )
                    )

                    print(
                        f"⏳ {wait_time} saniye bekleniyor..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                print(
                    "❌ Gemini retry limiti doldu."
                )

                return None

            # =================================================
            # SUNUCU HATALARI
            # =================================================

            if response.status_code in (
                500,
                502,
                503,
                504
            ):

                print(
                    "⚠️ Gemini sunucu hatası:",
                    response.status_code
                )

                if attempt < max_retries:

                    wait_time = (
                        8 * attempt
                        + random.randint(1, 5)
                    )

                    print(
                        f"⏳ {wait_time} saniye bekleniyor..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                return None

            # =================================================
            # DİĞER HATALAR
            # =================================================

            print(
                "❌ Gemini kalıcı hata:"
            )

            print(
                response.text[:5000]
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt < max_retries:

                wait_time = 10 * attempt

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue

            return None

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini bağlantı hatası:",
                str(e)
            )

            if attempt < max_retries:

                time.sleep(
                    10 * attempt
                )

                continue

            return None

    return None


# =========================================================
# AI
# =========================================================

def call_ai(prompt):

    result = call_gemini(prompt)

    if result:
        return result

    raise RuntimeError(
        "Gemini içerik üretemedi."
    )


# =========================================================
# GEÇMİŞ
# =========================================================

def load_history():

    if not os.path.exists(
        TOPIC_HISTORY_FILE
    ):
        return []

    try:

        with open(
            TOPIC_HISTORY_FILE,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):
                return data

    except Exception as e:

        print(
            "⚠️ Konu geçmişi okunamadı:",
            str(e)
        )

    return []


def save_history(history):

    with open(
        TOPIC_HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# KONU KONTROLÜ
# =========================================================

def is_valid_topic(topic):

    if not topic:
        return False

    if len(topic) < 8:
        return False

    if len(topic) > 220:
        return False

    if len(topic.split()) < 2:
        return False

    if not re.search(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}",
        topic
    ):
        return False

    return True


# =========================================================
# KONU + BÖLÜM PLANI
# =========================================================

def generate_topic_and_outline(history):

    if history:

        avoid_list = "\n".join(
            f"- {topic}"
            for topic in history[-50:]
        )

    else:

        avoid_list = "(henüz konu yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
YouTube kanalı için profesyonel belgesel
editörüsün.

KANAL NİŞİ:

Bilim insanlarının, mucitlerin ve
kaşiflerin gerçek ve dramatik hayat
hikayeleri.

Kuru bilgi anlatımı istemiyorum.

İzleyicide merak ve duygusal bağ
oluşturacak gerçek bir insan hikayesi
seç.

Mücadele, haksızlık, yalnızlık,
başarısızlık, geç tanınma, keşif,
zafer veya trajedi gibi gerçek
unsurlar kullanılabilir.

ÖRNEK KONU TARZLARI:

{ORNEK_KONULAR}

DAHA ÖNCE KULLANILAN KONULAR:

{avoid_list}

Daha önce kullanılan konulardan
birini kesinlikle seçme.

YENİ KONU:

Gerçek bir bilim insanı, mucit veya
kaşif seç.

Diktatör veya savaş suçlusu seçme.

Savaş tarihi seçme.

Genel tarih konusu seçme.

Günlük eşya konusu seçme.

Yaklaşık 30-45 dakikalık belgeseli
doldurabilecek kadar zengin bir
hikaye seç.

Bu istekte hem konuyu hem de
5 bölümlük planı oluştur.

HER BÖLÜM:

Yaklaşık 1100 kelimelik anlatımı
doldurabilecek içerik içermeli.

ÇIKTI TAM OLARAK ŞU FORMATTA OLSUN:

KONU: <konu>

BÖLÜM 1: <başlık> - <özet>
BÖLÜM 2: <başlık> - <özet>
BÖLÜM 3: <başlık> - <özet>
BÖLÜM 4: <başlık> - <özet>
BÖLÜM 5: <başlık> - <özet>

Markdown kullanma.
Yıldız kullanma.
Başka açıklama yazma.
"""

    return call_ai(prompt)


def parse_topic_outline(raw):

    topic = ""
    chapters = []

    for line in raw.splitlines():

        line = line.strip()

        if not line:
            continue

        clean = (
            line
            .replace("*", "")
            .replace("#", "")
            .strip()
        )

        upper = clean.upper()

        if upper.startswith("KONU:"):

            topic = (
                clean
                .split(":", 1)[1]
                .strip()
            )

        elif (
            upper.startswith("BÖLÜM")
            or upper.startswith("BOLUM")
        ):

            chapters.append(clean)

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip()

    return topic, chapters


# =========================================================
# BÖLÜM ÜRETİMİ
# =========================================================

def generate_chapter(
    topic,
    outline_text,
    chapter_line,
    chapter_index,
    total_chapters,
    previous_tail
):

    continuation = ""

    if previous_tail:

        continuation = f"""
ÖNCEKİ BÖLÜMÜN SON KISMI:

{previous_tail}

Bu bölüm buradan doğal biçimde
devam etmeli.

Önceki anlatımı tekrar etme.
"""

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı
Türkçe YouTube kanalı için profesyonel
belgesel anlatıcısısın.

GENEL KONU:

{topic}

BÖLÜM PLANI:

{outline_text}

ŞU ANDA YAZILAN BÖLÜM:

{chapter_line}

Yaklaşık {BOLUM_BASINA_KELIME}
kelimelik akıcı bir Türkçe belgesel
anlatımı oluştur.

Kişinin gerçek hayatını anlat.

Bilimsel çalışmalarını anlat.

Karşılaştığı gerçek sorunları anlat.

İnsan tarafını hissettir.

Dramatik anlatım kullan fakat
gerçeklerden ayrılma.

Uydurma diyalog oluşturma.

Uydurma alıntı oluşturma.

Bilgi uydurma.

{NARRATION_KURALLARI}

{continuation}

ÇIKTI SADECE SESLENDİRME METNİ OLSUN.

Bölüm başlığı yazma.

"Bölüm 1" yazma.

Sahne yazma.

Kamera yazma.

Müzik yazma.

Ses efekti yazma.

Parantez kullanma.

Köşeli parantez kullanma.

Metin doğrudan TTS sistemine
gönderilecektir.
"""

    return call_ai(prompt)


# =========================================================
# METADATA
# =========================================================

def generate_metadata(topic):

    prompt = f"""
Aşağıdaki Türkçe belgesel için
YouTube metadata oluştur.

KONU:

{topic}

Şu formatı kullan:

BAŞLIK:
Merak uyandırıcı fakat yanıltıcı
olmayan YouTube başlığı.

AÇIKLAMA:
3-5 cümlelik açıklama.

ETİKETLER:
15-25 Türkçe etiket, virgülle ayrılmış.

Sadece bu formatı yaz.
"""

    return call_ai(prompt)


def default_metadata(topic):

    return f"""
BAŞLIK:
{topic}

AÇIKLAMA:
{topic} hakkında gerçek olaylara dayanan
kapsamlı bir bilim ve tarih belgeseli.

ETİKETLER:
bilim, tarih, belgesel, bilim insanları,
keşif, mucitler, dahiler, bilgi,
bilim tarihi, tarih belgeseli
"""


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    os.makedirs(
        OUT,
        exist_ok=True
    )

    print("================================")
    print("🎬 30-45 DAKİKALIK BELGESEL MOTORU")
    print("================================")
    print(
        f"Hedef: {BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )
    print(
        f"Toplam hedef: "
        f"{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime"
    )
    print(
        "🧠 ANA AI: GEMINI"
    )
    print(
        "🚫 CEREBRAS KULLANILMIYOR"
    )
    print(
        "🚫 NVIDIA KULLANILMIYOR"
    )
    print("================================")
    print()

    history = load_history()

    topic = None
    chapters = []

    # =====================================================
    # KONU OLUŞTUR
    # =====================================================

    for attempt in range(1, 3):

        print(
            f"🔄 Konu denemesi "
            f"{attempt}/2"
        )

        try:

            raw = generate_topic_and_outline(
                history
            )

            if not raw:

                print(
                    "⚠️ Gemini boş cevap verdi."
                )
                continue

            print()
            print(
                "---- GEMINI KONU CEVABI ----"
            )

            print(
                raw[:3000]
            )

            print(
                "----------------------------"
            )

            candidate_topic, candidate_chapters = (
                parse_topic_outline(raw)
            )

            if (
                is_valid_topic(candidate_topic)
                and candidate_topic not in history
                and len(candidate_chapters) >= 5
            ):

                topic = candidate_topic

                chapters = (
                    candidate_chapters[:5]
                )

                break

            print(
                "⚠️ Geçersiz konu veya bölüm planı."
            )

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 2:

                time.sleep(10)

    if not topic:

        raise SystemExit(
            "❌ Gemini içerik üretemedi."
        )

    # =====================================================
    # KONU GÖSTER
    # =====================================================

    print()
    print(
        "🎯 KONU:",
        topic
    )

    print()

    for chapter in chapters:

        print(
            "📌",
            chapter
        )

    # =====================================================
    # GEÇMİŞE KAYDET
    # =====================================================

    if topic not in history:

        history.append(
            topic
        )

        save_history(
            history
        )

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            topic
        )

    # =====================================================
    # BÖLÜMLERİ ÜRET
    # =====================================================

    print()
    print(
        "================================"
    )
    print(
        "✍️ BÖLÜMLER GEMINI İLE YAZILIYOR"
    )
    print(
        "================================"
    )

    outline_text = "\n".join(
        chapters
    )

    script_parts = []

    previous_tail = ""

    for index, chapter in enumerate(
        chapters,
        1
    ):

        print()
        print(
            f"📝 BÖLÜM {index}/{len(chapters)}"
        )

        try:

            chapter_text = generate_chapter(
                topic,
                outline_text,
                chapter,
                index,
                len(chapters),
                previous_tail
            )

        except Exception as e:

            print(
                f"❌ Bölüm {index} üretilemedi:"
            )

            print(
                str(e)
            )

            raise SystemExit(1)

        if not chapter_text:

            raise SystemExit(
                f"❌ Bölüm {index} boş geldi."
            )

        word_count = len(
            chapter_text.split()
        )

        print(
            f"✅ Bölüm {index}: "
            f"{word_count} kelime"
        )

        script_parts.append(
            chapter_text.strip()
        )

        previous_tail = (
            chapter_text[-700:]
        )

    # =====================================================
    # TAM METİN
    # =====================================================

    full_script = "\n\n".join(
        script_parts
    )

    total_words = len(
        full_script.split()
    )

    print()
    print(
        "================================"
    )
    print(
        "📊 TOPLAM KELİME:",
        total_words
    )
    print(
        "================================"
    )

    # =====================================================
    # METADATA
    # =====================================================

    metadata_text = None

    try:

        print()
        print(
            "🏷️ Metadata Gemini ile oluşturuluyor..."
        )

        metadata_text = generate_metadata(
            topic
        )

    except Exception as e:

        print(
            "⚠️ Metadata oluşturulamadı:",
            str(e)
        )

    if not metadata_text:

        metadata_text = default_metadata(
            topic
        )

    # =====================================================
    # DOSYAYA YAZ
    # =====================================================

    final_content = (
        full_script
        + "\n\n"
        + METADATA_AYIRICI
        + "\n\n"
        + metadata_text.strip()
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            final_content
        )

    print()
    print(
        "================================"
    )
    print(
        "✅ İÇERİK OLUŞTURULDU"
    )
    print(
        "================================"
    )
    print(
        "📁 Dosya:",
        OUTPUT_FILE
    )
    print(
        "📝 Kelime:",
        total_words
    )
    print(
        "🎯 Konu:",
        topic
    )
    print(
        "🧠 Üretici: Gemini"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    main()
