import os
import json
import requests
import re
import time
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# GEMINI API KEY
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if not GEMINI_API_KEY:
    raise RuntimeError(
        "❌ GEMINI_API_KEY bulunamadı. "
        "GitHub Secrets bölümünü kontrol et."
    )

# ============================================================
# DOSYALAR
# ============================================================

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

# ============================================================
# GEMINI
# ============================================================

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

MAX_RETRIES = 3

# ============================================================
# VİDEO AYARLARI
# ============================================================

HEDEF_DAKIKA = 15

# Ortalama Türkçe konuşma hızına göre yaklaşık hedef.
HEDEF_KELIME = 2200

MAX_HISTORY = 30

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# ============================================================
# BELGESEL KURALLARI
# ============================================================

NARRATION_KURALLARI = """
KURALLAR:

1. Bilgi uydurma.
2. Tarihleri, olayları, kişileri ve yerleri mümkün olduğunca doğru aktar.
3. Emin olunmayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı ve kronolojik bir akışla anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Güçlü bir giriş yap ve izleyicinin merakını canlı tut.
10. Belgeselin sonunda güçlü ve akılda kalıcı bir kapanış yap.
11. Metin doğrudan TTS sistemine gönderilecektir.
12. Cümleler doğal seslendirmeye uygun olmalıdır.

ÖNEMLİ:

Bu bir film senaryosu değildir.

Sahne yazma.
Kamera hareketi yazma.
Karakter hareketi yazma.
Müzik yazma.
Ses efekti yazma.
Parantez kullanma.
Köşeli parantez kullanma.

"[Hüzünlü müzik]"
"(kamera yaklaşır)"
"Sahne 1"
"Bölüm 1"

gibi ifadeler kesinlikle yazma.

İzleyici bunun yapay olarak oluşturulmuş bölümlere ayrılmış
bir metin olduğunu hissetmemeli.

Anlatım tek parça ve kesintisiz bir belgesel gibi ilerlemeli.

SADECE seçilen konuyu anlat.

Metin doğrudan TTS sistemine gönderileceği için
okuyucu yalnızca gerçek anlatım cümlelerini görmelidir.
"""

# ============================================================
# GEMINI ÇAĞRISI
# ============================================================

def call_gemini(prompt, max_retries=MAX_RETRIES):

    for attempt in range(
        1,
        max_retries + 1
    ):

        print(
            f"🤖 Gemini isteği "
            f"{attempt}/{max_retries}"
        )

        try:

            response = requests.post(
                GEMINI_URL,
                params={
                    "key": GEMINI_API_KEY
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
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 12000
                    }
                },
                timeout=300
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            # ------------------------------------------------
            # BAŞARILI
            # ------------------------------------------------

            if response.ok:

                data = response.json()

                try:

                    text = (
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

                    if text and text.strip():

                        print(
                            "✅ Gemini içerik üretimi başarılı."
                        )

                        return text.strip()

                    print(
                        "❌ Gemini boş cevap döndürdü."
                    )

                    return None

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):

                    print(
                        "❌ Gemini cevabı beklenen formatta değil."
                    )

                    print(
                        response.text[:2000]
                    )

                    return None

            # ------------------------------------------------
            # KOTA
            # ------------------------------------------------

            if response.status_code == 429:

                print(
                    "❌ Gemini 429 / kota sınırı."
                )

                print(
                    "⚠️ İşlem durduruluyor."
                )

                return None

            # ------------------------------------------------
            # SUNUCU HATALARI
            # ------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt >= max_retries:

                    print(
                        "❌ Gemini sunucu hatası."
                    )

                    return None

                wait_time = (
                    10 * (2 ** (attempt - 1))
                    + random.randint(0, 5)
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # ------------------------------------------------
            # DİĞER HATALAR
            # ------------------------------------------------

            print(
                "❌ Gemini kalıcı hata:"
            )

            print(
                response.text[:3000]
            )

            return None

        # ----------------------------------------------------
        # TIMEOUT
        # ----------------------------------------------------

        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt >= max_retries:

                print(
                    "❌ Gemini timeout nedeniyle başarısız."
                )

                return None

            wait_time = 10 * attempt

            print(
                f"⏳ {wait_time} saniye bekleniyor..."
            )

            time.sleep(
                wait_time
            )

        # ----------------------------------------------------
        # NETWORK
        # ----------------------------------------------------

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini ağ hatası:",
                str(e)
            )

            if attempt >= max_retries:

                print(
                    "❌ Gemini ağ hatası nedeniyle başarısız."
                )

                return None

            wait_time = 10 * attempt

            print(
                f"⏳ {wait_time} saniye bekleniyor..."
            )

            time.sleep(
                wait_time
            )

    return None


# ============================================================
# GEÇMİŞ
# ============================================================

def load_history():

    if not os.path.exists(
        TOPIC_HISTORY_FILE
    ):

        return []

    try:

        with open(
            TOPIC_HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(
                data,
                list
            ):

                return data

            return []

    except Exception as e:

        print(
            "⚠️ Konu geçmişi okunamadı:",
            str(e)
        )

        return []


def save_history(history):

    history = history[
        -MAX_HISTORY:
    ]

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


# ============================================================
# KONU KONTROLÜ
# ============================================================

def is_valid_topic(topic):

    if not topic:

        return False

    topic = topic.strip()

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


# ============================================================
# KONU + 15 DAKİKALIK BELGESEL
# TEK GEMINI İSTEĞİ
# ============================================================

def generate_full_documentary(
    history
):

    avoid_list = (
        "\n".join(
            f"- {topic}"
            for topic in history
        )
        if history
        else "(henüz konu yok)"
    )

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
tarih, bilim ve keşif YouTube kanalı için
profesyonel belgesel yazarı ve editörsün.

Bu istekte HER ŞEYİ TEK SEFERDE oluştur.

ÖNEMLİ:

Sadece BİR API isteği yapılıyor.

Yaklaşık 15 dakikalık,
tek parça,
kesintisiz,
profesyonel Türkçe belgesel üret.

Hedef yaklaşık {HEDEF_KELIME} kelimedir.

Daha önce kullanılan konular:

{avoid_list}

==================================================
KONU SEÇİMİ
==================================================

İlgi çekici, gerçek ve doğrulanabilir
bir tarih, bilim, keşif veya önemli kişi konusu seç.

Konu yaklaşık 15 dakikalık anlatımı
doldurabilecek kadar zengin olmalıdır.

Daha önce kullanılan konuları tekrar etme.

Diktatör veya savaş suçlusu seçme.

Propaganda veya kışkırtıcı içerik üretme.

==================================================
BELGESEL
==================================================

Seçtiğin konu hakkında yaklaşık
{HEDEF_KELIME} kelimelik
tek parça belgesel anlatımı yaz.

Belgesel:

- güçlü bir girişe sahip olmalı
- izleyicide merak oluşturmalı
- olayları mantıklı sırayla anlatmalı
- önemli tarihleri ve kişileri vermeli
- konunun neden önemli olduğunu açıklamalı
- gereksiz tekrar içermemeli
- doğal Türkçe ile yazılmalı
- yaklaşık 15 dakika sürmeli
- güçlü bir final ile bitmeli

Kesinlikle bölüm oluşturma.

"Bölüm 1"
"Bölüm 2"
gibi ifadeler kullanma.

Metni parçalara ayırma.

==================================================
METADATA
==================================================

Belgesel metninin sonunda aşağıdaki ayırıcıyı
AYNEN kullan:

{METADATA_AYIRICI}

Daha sonra:

BAŞLIK:
Merak uyandırıcı, profesyonel ve yanıltıcı olmayan
bir YouTube başlığı yaz.

AÇIKLAMA:
Belgeseli özetleyen 3-5 cümlelik
YouTube açıklaması yaz.

ETİKETLER:
15-25 adet Türkçe etiketi virgülle ayırarak yaz.

==================================================
ANLATIM KURALLARI
==================================================

{NARRATION_KURALLARI}

==================================================
ÇIKTI FORMATI
==================================================

Önce yalnızca belgesel anlatımı.

Sonra:

{METADATA_AYIRICI}

BAŞLIK:
...

AÇIKLAMA:
...

ETİKETLER:
...

Başka açıklama veya yorum yazma.
"""

    return call_gemini(
        prompt
    )


# ============================================================
# METADATA AYIR
# ============================================================

def parse_documentary(
    raw_text
):

    if not raw_text:

        return "", None

    if METADATA_AYIRICI in raw_text:

        narration, metadata = (
            raw_text.split(
                METADATA_AYIRICI,
                1
            )
        )

        return (
            narration.strip(),
            metadata.strip()
        )

    return (
        raw_text.strip(),
        None
    )


# ============================================================
# VARSAYILAN METADATA
# ============================================================

def default_metadata(
    topic
):

    return (
        "BAŞLIK:\n"
        f"{topic[:95]}\n\n"
        "AÇIKLAMA:\n"
        f"{topic} hakkında yaklaşık 15 dakikalık "
        "kapsamlı bir belgesel.\n\n"
        "ETİKETLER:\n"
        "tarih, bilim, belgesel, keşif, bilgi"
    )


# ============================================================
# ANA
# ============================================================

def main():

    print(
        "================================"
    )

    print(
        "🎬 15 DAKİKALIK BELGESEL MOTORU"
    )

    print(
        "================================"
    )

    print(
        f"🎯 Hedef süre: yaklaşık "
        f"{HEDEF_DAKIKA} dakika"
    )

    print(
        f"📝 Hedef kelime: yaklaşık "
        f"{HEDEF_KELIME}"
    )

    print(
        "🤖 AI: Gemini"
    )

    print(
        "📡 API isteği: TEK İSTEK"
    )

    print(
        "================================"
    )

    os.makedirs(
        OUT,
        exist_ok=True
    )

    history = load_history()

    print()

    print(
        "🧠 Konu + 15 dakikalık "
        "belgesel tek istekte oluşturuluyor..."
    )

    raw = generate_full_documentary(
        history
    )

    if not raw:

        raise SystemExit(
            "❌ Gemini içerik üretemedi."
        )

    narration, metadata = (
        parse_documentary(
            raw
        )
    )

    if not narration:

        raise SystemExit(
            "❌ Belgesel metni boş geldi."
        )

    # ========================================================
    # KONUYU METADATA'DAN VEYA METİNDEN AL
    # ========================================================

    topic = ""

    if metadata:

        match = re.search(
            r"BAŞLIK:\s*(.+)",
            metadata,
            re.IGNORECASE
        )

        if match:

            topic = match.group(
                1
            ).strip()

    if not topic:

        first_sentence = re.split(
            r"[.!?]",
            narration
        )[0].strip()

        topic = first_sentence[
            :180
        ]

    if not topic:

        topic = "Yeni Belgesel"

    # ========================================================
    # KONU GEÇMİŞİ
    # ========================================================

    if (
        is_valid_topic(topic)
        and topic not in history
    ):

        history.append(
            topic
        )

        save_history(
            history
        )

    # ========================================================
    # TOPIC DOSYASI
    # ========================================================

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            topic
        )

    # ========================================================
    # KELİME / SÜRE
    # ========================================================

    toplam_kelime = len(
        narration.split()
    )

    # Ortalama 150 kelime/dakika
    tahmini_dakika = round(
        toplam_kelime / 150,
        1
    )

    print()

    print(
        "================================"
    )

    print(
        "📊 BELGESEL BİLGİLERİ"
    )

    print(
        "================================"
    )

    print(
        "🎯 Konu:",
        topic
    )

    print(
        "📝 Kelime:",
        toplam_kelime
    )

    print(
        "⏱️ Tahmini süre:",
        tahmini_dakika,
        "dakika"
    )

    print(
        "================================"
    )

    # ========================================================
    # METADATA
    # ========================================================

    if not metadata:

        metadata = default_metadata(
            topic
        )

    # ========================================================
    # DOSYAYA YAZ
    # ========================================================

    final_text = (
        "=== SESLENDİRME METNİ ===\n"
        + narration
        + "\n\n"
        + "=== METADATA ===\n"
        + metadata
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            final_text
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
        "🤖 AI: Gemini"
    )

    print(
        "📡 API isteği: 1"
    )

    print(
        "📝 Toplam kelime:",
        toplam_kelime
    )

    print(
        "⏱️ Tahmini dakika:",
        tahmini_dakika
    )

    print(
        "📁 Dosya:",
        OUTPUT_FILE
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
