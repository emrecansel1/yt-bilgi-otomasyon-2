import os
import json
import re
import time
import random
import requests


# =========================================================
# DİZİNLER
# =========================================================

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(
    REPO_BASE,
    "video_topic_history.json"
)
OUTPUT_FILE = os.path.join(
    OUT,
    "current_content.txt"
)


# =========================================================
# API ANAHTARLARI
# =========================================================

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    ""
).strip()

CEREBRAS_API_KEY = os.environ.get(
    "CEREBRAS_API_KEY",
    ""
).strip()

NVIDIA_API_KEY = os.environ.get(
    "NVIDIA_API_KEY",
    ""
).strip()


print("================================")
print("🔐 API DURUMU")
print("================================")

if GEMINI_API_KEY:
    print("✅ GEMINI_API_KEY mevcut.")
else:
    print("⚠️ GEMINI_API_KEY yok.")

if CEREBRAS_API_KEY:
    print("✅ CEREBRAS_API_KEY mevcut.")
else:
    print("⚠️ CEREBRAS_API_KEY yok.")

if NVIDIA_API_KEY:
    print("✅ NVIDIA_API_KEY mevcut.")
else:
    print("⚠️ NVIDIA_API_KEY yok.")

print("================================")


# =========================================================
# GÜNCEL MODEL AYARLARI
# =========================================================

# Google tarafında kararlı Gemini modeli
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)


# Cerebras güncel üretim modeli
CEREBRAS_URL = (
    "https://api.cerebras.ai/v1/chat/completions"
)

CEREBRAS_MODEL = "gpt-oss-120b"


# NVIDIA eski model SABİT OLARAK KULLANILMIYOR.
NVIDIA_CHAT_URL = (
    "https://integrate.api.nvidia.com/v1/chat/completions"
)

NVIDIA_MODELS_URL = (
    "https://integrate.api.nvidia.com/v1/models"
)


# =========================================================
# BELGESEL AYARLARI
# =========================================================

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100

TOPLAM_HEDEF = (
    BOLUM_SAYISI *
    BOLUM_BASINA_KELIME
)

METADATA_AYIRICI = "===METADATA_AYIRICI==="


# =========================================================
# ÖRNEK KONU HAVUZU
# =========================================================

ORNEK_KONULAR = """
Semmelweis'in el yıkama önerisi yüzünden dışlanması
Nikola Tesla'nın hayatının son dönemindeki yalnızlığı
Alan Turing'in savaşa katkısı ve sonrasında yaşadıkları
Rosalind Franklin'in DNA araştırmalarındaki rolü
Marie Curie'nin radyasyon araştırmaları ve bedeli
Ludwig Boltzmann'ın bilim dünyasındaki mücadelesi
Barbara McClintock'un keşfinin yıllarca kabul edilmemesi
Galileo Galilei'nin bilimsel fikirleri nedeniyle yargılanması
Giordano Bruno'nun fikirleri nedeniyle idam edilmesi
Évariste Galois'nın kısa ve trajik hayatı
Vera Rubin'in karanlık madde araştırmaları
Jocelyn Bell Burnell'in pulsar keşfi
Emmy Noether'in akademide karşılaştığı engeller
Ada Lovelace'in matematik ve programlama tarihindeki rolü
Katherine Johnson'un NASA'daki bilimsel mücadelesi
Srinivasa Ramanujan'ın sıra dışı matematik hayatı
Kurt Gödel'in hayatının son dönemi
Antoine Lavoisier'in bilimsel çalışmaları ve idamı
"""


# =========================================================
# ANLATIM KURALLARI
# =========================================================

NARRATION_KURALLARI = """
Bilgi uydurma.

Tarihleri ve olayları mümkün olduğunca doğru aktar.

Kesinliği bilinmeyen olayları kesin gerçek gibi sunma.

Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.

Gereksiz tekrar yapma.

Kuru ansiklopedi anlatımı yapma.

Bilim insanının insani tarafını hissettir.

Mücadele, haksızlık, yalnızlık, başarısızlık, umut,
başarı ve bilimsel katkı arasında doğal bağ kur.

Bilimsel kavramları herkesin anlayabileceği şekilde açıkla.

Önemli kişiler, tarihler, yerler ve olaylara yer ver.

Metin doğrudan TTS sistemine gönderilecektir.

Sahne açıklaması yazma.

Kamera hareketi yazma.

Müzik yazma.

Ses efekti yazma.

Parantez kullanma.

Köşeli parantez kullanma.

"Bölüm 1", "Sahne 1" gibi ifadeler yazma.

Başlangıçta "Merhaba arkadaşlar" gibi YouTube klişeleri kullanma.

Metin doğrudan belgesel anlatımı şeklinde başlamalıdır.

İzleyici bunun ayrı bölümlerden oluştuğunu hissetmemelidir.

Anlatım tek ve kesintisiz bir belgesel gibi akmalıdır.
"""


# =========================================================
# YARDIMCI
# =========================================================

def clean_text(text):
    if not text:
        return ""

    text = text.replace(
        METADATA_AYIRICI,
        ""
    )

    text = re.sub(
        r"\[.*?\]",
        "",
        text
    )

    text = re.sub(
        r"\(.*?\)",
        "",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


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

            if isinstance(data, list):
                return data

    except Exception as e:
        print(
            "⚠️ Konu geçmişi okunamadı:",
            str(e)
        )

    return []


def save_history(history):

    try:

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

    except Exception as e:

        print(
            "⚠️ Konu geçmişi kaydedilemedi:",
            str(e)
        )


def valid_topic(topic):

    if not topic:
        return False

    topic = topic.strip()

    if len(topic) < 10:
        return False

    if len(topic) > 220:
        return False

    if len(topic.split()) < 2:
        return False

    return True


# =========================================================
# GEMINI
# =========================================================

def call_gemini(
    prompt,
    max_retries=2
):

    if not GEMINI_API_KEY:
        print(
            "❌ Gemini API key yok."
        )
        return None

    for attempt in range(
        1,
        max_retries + 1
    ):

        print(
            f"🤖 Gemini "
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
                        "maxOutputTokens": 16000
                    }
                },

                timeout=180
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            if response.ok:

                data = response.json()

                candidates = data.get(
                    "candidates",
                    []
                )

                if not candidates:
                    print(
                        "❌ Gemini candidate yok."
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
                        "❌ Gemini text yok."
                    )
                    return None

                text = parts[0].get(
                    "text",
                    ""
                )

                if text.strip():
                    return text.strip()

                return None


            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429 "
                    "kota/rate limit."
                )

                # Uzun uzun retry yapıp GitHub Actions
                # süresini tüketme.
                return None


            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt < max_retries:

                    wait = (
                        5 * attempt
                        + random.randint(1, 4)
                    )

                    print(
                        f"⏳ {wait} saniye..."
                    )

                    time.sleep(wait)

                    continue

                return None


            print(
                "❌ Gemini kalıcı hata:"
            )

            print(
                response.text[:2000]
            )

            return None


        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt < max_retries:
                time.sleep(5)
                continue

            return None


        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini ağ hatası:",
                str(e)
            )

            if attempt < max_retries:
                time.sleep(5)
                continue

            return None

    return None


# =========================================================
# CEREBRAS
# =========================================================

def call_cerebras(
    prompt,
    max_retries=2
):

    if not CEREBRAS_API_KEY:

        print(
            "❌ CEREBRAS_API_KEY yok."
        )

        return None


    headers = {

        "Authorization":
            f"Bearer {CEREBRAS_API_KEY}",

        "Content-Type":
            "application/json"
    }


    payload = {

        "model":
            CEREBRAS_MODEL,

        "messages": [

            {
                "role": "system",

                "content":
                    "Sen profesyonel Türkçe "
                    "tarih ve bilim belgeseli "
                    "yazarı olarak görev yapıyorsun."
            },

            {
                "role": "user",

                "content":
                    prompt
            }
        ],

        "temperature":
            0.7,

        "max_tokens":
            16000
    }


    for attempt in range(
        1,
        max_retries + 1
    ):

        print(
            f"🟢 Cerebras "
            f"{attempt}/{max_retries}"
        )

        try:

            response = requests.post(

                CEREBRAS_URL,

                headers=headers,

                json=payload,

                timeout=180
            )

            print(
                "Cerebras HTTP:",
                response.status_code
            )


            if response.ok:

                data = response.json()

                choices = data.get(
                    "choices",
                    []
                )

                if not choices:
                    print(
                        "❌ Cerebras choices yok."
                    )
                    return None

                message = choices[0].get(
                    "message",
                    {}
                )

                text = message.get(
                    "content",
                    ""
                )

                if text.strip():
                    return text.strip()

                return None


            if response.status_code == 401:

                print(
                    "❌ Cerebras API key "
                    "GEÇERSİZ."
                )

                print(
                    "ℹ️ GitHub Secrets → "
                    "CEREBRAS_API_KEY "
                    "kontrol edilmeli."
                )

                return None


            if response.status_code == 429:

                print(
                    "⚠️ Cerebras 429."
                )

                if attempt < max_retries:

                    wait = 10 * attempt

                    print(
                        f"⏳ {wait} saniye..."
                    )

                    time.sleep(wait)

                    continue

                return None


            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt < max_retries:

                    time.sleep(
                        5 * attempt
                    )

                    continue

                return None


            print(
                "❌ Cerebras kalıcı hata:"
            )

            print(
                response.text[:2000]
            )

            return None


        except requests.exceptions.Timeout:

            print(
                "⚠️ Cerebras timeout."
            )

            if attempt < max_retries:

                time.sleep(5)

                continue

            return None


        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Cerebras ağ hatası:",
                str(e)
            )

            if attempt < max_retries:

                time.sleep(5)

                continue

            return None

    return None


# =========================================================
# NVIDIA MODEL BUL
# =========================================================

def get_nvidia_model():

    if not NVIDIA_API_KEY:
        return None

    headers = {
        "Authorization":
            f"Bearer {NVIDIA_API_KEY}"
    }

    try:

        response = requests.get(

            NVIDIA_MODELS_URL,

            headers=headers,

            timeout=30
        )

        print(
            "NVIDIA models HTTP:",
            response.status_code
        )

        if not response.ok:

            print(
                "⚠️ NVIDIA model listesi "
                "alınamadı."
            )

            print(
                response.text[:1000]
            )

            return None


        data = response.json()

        models = data.get(
            "data",
            []
        )

        if not models:
            print(
                "⚠️ NVIDIA kullanılabilir "
                "model listesi boş."
            )
            return None


        # Öncelikli adaylar.
        tercih = [

            "openai/gpt-oss-120b",

            "meta/llama-3.1-70b-instruct",

            "meta/llama-3.1-8b-instruct",

            "mistralai/mistral-small-24b-instruct-2501"
        ]


        available = []

        for item in models:

            model_id = item.get(
                "id",
                ""
            )

            if model_id:
                available.append(
                    model_id
                )


        print(
            "🧠 NVIDIA kullanılabilir "
            f"model sayısı: {len(available)}"
        )


        for wanted in tercih:

            if wanted in available:

                print(
                    "✅ NVIDIA model bulundu:",
                    wanted
                )

                return wanted


        # Tercihli model yoksa
        # metin üretmeye uygun görünen ilk modeli seç.
        for model_id in available:

            lower = model_id.lower()

            if any(
                x in lower
                for x in [
                    "llama",
                    "gpt",
                    "mistral",
                    "qwen",
                    "nemotron"
                ]
            ):

                print(
                    "✅ NVIDIA alternatif model:",
                    model_id
                )

                return model_id


        return None


    except Exception as e:

        print(
            "⚠️ NVIDIA model listesi hatası:",
            str(e)
        )

        return None


# =========================================================
# NVIDIA
# =========================================================

def call_nvidia(
    prompt,
    max_retries=1
):

    if not NVIDIA_API_KEY:

        print(
            "❌ NVIDIA_API_KEY yok."
        )

        return None


    model = get_nvidia_model()

    if not model:

        print(
            "❌ NVIDIA'da kullanılabilir "
            "model bulunamadı."
        )

        return None


    headers = {

        "Authorization":
            f"Bearer {NVIDIA_API_KEY}",

        "Content-Type":
            "application/json"
    }


    payload = {

        "model":
            model,

        "messages": [

            {
                "role": "system",

                "content":
                    "Sen profesyonel Türkçe "
                    "tarih ve bilim belgeseli "
                    "yazarı olarak görev yapıyorsun."
            },

            {
                "role": "user",

                "content":
                    prompt
            }
        ],

        "temperature":
            0.7,

        "max_tokens":
            12000
    }


    for attempt in range(
        1,
        max_retries + 1
    ):

        print(
            f"🟩 NVIDIA "
            f"{attempt}/{max_retries}"
        )

        print(
            "🧠 NVIDIA model:",
            model
        )

        try:

            response = requests.post(

                NVIDIA_CHAT_URL,

                headers=headers,

                json=payload,

                timeout=120
            )

            print(
                "NVIDIA HTTP:",
                response.status_code
            )


            if response.ok:

                data = response.json()

                choices = data.get(
                    "choices",
                    []
                )

                if not choices:
                    print(
                        "❌ NVIDIA choices yok."
                    )
                    return None

                text = choices[0].get(
                    "message",
                    {}
                ).get(
                    "content",
                    ""
                )

                if text.strip():
                    return text.strip()

                return None


            if response.status_code == 401:

                print(
                    "❌ NVIDIA API key geçersiz."
                )

                return None


            if response.status_code == 429:

                print(
                    "⚠️ NVIDIA 429."
                )

                return None


            if response.status_code == 410:

                print(
                    "❌ NVIDIA seçilen model "
                    "artık kullanılamıyor."
                )

                print(
                    response.text[:1500]
                )

                return None


            print(
                "❌ NVIDIA hata:"
            )

            print(
                response.text[:2000]
            )

            return None


        except requests.exceptions.Timeout:

            print(
                "⚠️ NVIDIA timeout."
            )

            return None


        except requests.exceptions.RequestException as e:

            print(
                "⚠️ NVIDIA ağ hatası:",
                str(e)
            )

            return None

    return None


# =========================================================
# ANA AI FALLBACK
# =========================================================

def call_ai(prompt):

    # -----------------------------------------------------
    # 1 - GEMINI
    # -----------------------------------------------------

    if GEMINI_API_KEY:

        print()
        print(
            "================================"
        )
        print(
            "🤖 ANA SİSTEM: GEMINI"
        )
        print(
            "================================"
        )

        result = call_gemini(
            prompt
        )

        if result:

            print(
                "✅ Gemini başarılı."
            )

            return result


    # -----------------------------------------------------
    # 2 - CEREBRAS
    # -----------------------------------------------------

    if CEREBRAS_API_KEY:

        print()
        print(
            "================================"
        )
        print(
            "🟢 YEDEK SİSTEM: CEREBRAS"
        )
        print(
            "================================"
        )

        result = call_cerebras(
            prompt
        )

        if result:

            print(
                "✅ Cerebras başarılı."
            )

            return result

    else:

        print(
            "⚠️ Cerebras API key yok."
        )


    # -----------------------------------------------------
    # 3 - NVIDIA
    # -----------------------------------------------------

    if NVIDIA_API_KEY:

        print()
        print(
            "================================"
        )
        print(
            "🟩 YEDEK SİSTEM: NVIDIA"
        )
        print(
            "================================"
        )

        result = call_nvidia(
            prompt
        )

        if result:

            print(
                "✅ NVIDIA başarılı."
            )

            return result

    else:

        print(
            "⚠️ NVIDIA API key yok."
        )


    raise RuntimeError(
        "Gemini, Cerebras ve NVIDIA "
        "başarılı bir cevap veremedi."
    )


# =========================================================
# KONU + PLAN
# =========================================================

def generate_topic_and_outline(
    history
):

    avoid = "\n".join(
        f"- {x}"
        for x in history[-100:]
    )

    if not avoid:
        avoid = "(Henüz konu yok.)"


    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı
Türkçe bilim ve tarih YouTube kanalı
için belgesel editörüsün.

KANAL NİŞİ:

Bilim insanlarının, mucitlerin ve
kaşiflerin gerçek ve dramatik
hikayelerini anlat.

Kuru bilgi verme.

İnsani mücadele, haksızlık, yalnızlık,
başarısızlık, başarı, dışlanma,
geç kabul edilme veya bilim uğruna
ödenen bedel gibi unsurlar önemli.

ÖRNEK KONU TARZLARI:

{ORNEK_KONULAR}

DAHA ÖNCE KULLANILAN KONULAR:

{avoid}

Daha önce kullanılan konuları
tekrar seçme.

Tek bir gerçek bilim insanı,
mucit veya kaşif seç.

Savaş tarihi, genel tarih,
diktatör, savaş suçlusu,
günlük eşya veya genel merak
konusu seçme.

Seçtiğin kişinin hikayesi
30-45 dakikalık belgeseli
doldurabilecek kadar zengin olmalı.

5 bölüm planla.

ÇIKTIYI TAM OLARAK ŞU FORMATTA VER:

KONU: kişi ve olay

BÖLÜM 1: başlık - kısa özet

BÖLÜM 2: başlık - kısa özet

BÖLÜM 3: başlık - kısa özet

BÖLÜM 4: başlık - kısa özet

BÖLÜM 5: başlık - kısa özet

Sadece düz metin kullan.
Markdown kullanma.
"""


    raw = call_ai(
        prompt
    )

    if not raw:
        return "", []


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


        if upper.startswith(
            "KONU:"
        ):

            topic = clean.split(
                ":",
                1
            )[1].strip()


        elif (
            upper.startswith("BÖLÜM")
            or
            upper.startswith("BOLUM")
        ):

            chapters.append(
                clean
            )


    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip()


    print()
    print(
        "---- KONU ÇIKTISI ----"
    )

    print(
        "🎯 Konu:",
        topic
    )

    print(
        "📚 Bölüm:",
        len(chapters)
    )

    for chapter in chapters:
        print(
            chapter
        )

    print(
        "----------------------"
    )


    return (
        topic,
        chapters
    )


# =========================================================
# BÖLÜM ÜRET
# =========================================================

def generate_chapter(
    topic,
    outline,
    chapter_line,
    chapter_index,
    previous_tail
):

    continuity = ""

    if previous_tail:

        continuity = f"""

ÖNCEKİ BÖLÜMÜN SONUNDAN KISA KISIM:

{previous_tail}

Buradan doğal şekilde devam et.

Aynı cümleleri veya bilgileri
tekrar etme.
"""


    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı
Türkçe bilim/tarih YouTube kanalı
için profesyonel belgesel anlatıcısısın.

ANA KONU:

{topic}

TÜM BÖLÜM PLANI:

{outline}

ŞU ANDA YAZILAN KISIM:

{chapter_line}

Bu kısım yaklaşık
{BOLUM_BASINA_KELIME} kelime olmalı.

{continuity}

{NARRATION_KURALLARI}

ÇOK ÖNEMLİ:

Metni doğrudan seslendirme için yaz.

Başlık yazma.

Bölüm numarası yazma.

"Bu bölümde..." deme.

Sahne yazma.

Kamera yazma.

Müzik yazma.

Parantez kullanma.

Metin doğal bir belgesel anlatımı
gibi başlamalı ve bitmeli.

Sonraki bölüme geçişi doğal bırak.
"""


    raw = call_ai(
        prompt
    )

    if not raw:
        return ""

    return clean_text(
        raw
    )


# =========================================================
# METADATA
# =========================================================

def generate_metadata(topic):

    prompt = f"""
{topic}

Bu belgesel için YouTube metadata
oluştur.

Şu formatı kullan:

BAŞLIK:
Merak uyandırıcı gerçekçi başlık

AÇIKLAMA:
3-5 cümle

ETİKETLER:
15-25 Türkçe etiket, virgülle ayrılmış

Sadece bu formatı kullan.
"""


    try:

        raw = call_ai(
            prompt
        )

        if raw:
            return raw.strip()

    except Exception as e:

        print(
            "⚠️ Metadata üretilemedi:",
            str(e)
        )


    return (
        f"BAŞLIK:\n"
        f"{topic}\n\n"
        f"AÇIKLAMA:\n"
        f"{topic} hakkında "
        f"bilim ve tarih belgeseli.\n\n"
        f"ETİKETLER:\n"
        f"bilim, tarih, belgesel, "
        f"bilim insanları, keşif"
    )


# =========================================================
# ANA
# =========================================================

def main():

    os.makedirs(
        OUT,
        exist_ok=True
    )


    print()
    print(
        "================================"
    )
    print(
        "🎬 30-45 DAKİKALIK "
        "BELGESEL MOTORU"
    )
    print(
        "================================"
    )

    print(
        f"Hedef: "
        f"{BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )

    print(
        f"Toplam hedef: "
        f"{TOPLAM_HEDEF} kelime"
    )

    print(
        f"Ana AI: Gemini "
        f"({GEMINI_MODEL})"
    )

    print(
        f"1. Yedek: Cerebras "
        f"({CEREBRAS_MODEL})"
    )

    print(
        "2. Yedek: NVIDIA "
        "(otomatik model keşfi)"
    )

    print(
        "================================"
    )


    history = load_history()


    # =====================================================
    # KONU
    # =====================================================

    topic = None
    chapters = []


    for attempt in range(
        1,
        4
    ):

        print()
        print(
            f"🔄 Konu denemesi "
            f"{attempt}/3"
        )

        try:

            candidate_topic, candidate_chapters = (
                generate_topic_and_outline(
                    history
                )
            )


            if (
                valid_topic(
                    candidate_topic
                )
                and
                candidate_topic not in history
                and
                len(candidate_chapters) >= 5
            ):

                topic = candidate_topic

                chapters = (
                    candidate_chapters[:5]
                )

                break


            print(
                "⚠️ Konu veya bölüm "
                "planı geçersiz."
            )


        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 3:
                time.sleep(3)


    if not topic:

        raise SystemExit(
            "❌ Geçerli konu üretilemedi."
        )


    # =====================================================
    # KAYDET
    # =====================================================

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


    outline_text = "\n".join(
        chapters
    )


    print()
    print(
        "🎯 SEÇİLEN KONU:",
        topic
    )

    print()
    print(
        "📚 BÖLÜM PLANI:"
    )

    for chapter in chapters:

        print(
            " -",
            chapter
        )


    # =====================================================
    # BÖLÜMLER
    # =====================================================

    print()
    print(
        "================================"
    )
    print(
        "✍️ BELGESEL METNİ ÜRETİLİYOR"
    )
    print(
        "================================"
    )


    script_parts = []

    previous_tail = ""


    for index, chapter in enumerate(
        chapters,
        1
    ):

        print()
        print(
            f"📝 Bölüm "
            f"{index}/{len(chapters)}"
        )


        success = False


        for retry in range(
            1,
            3
        ):

            try:

                text = generate_chapter(

                    topic,

                    outline_text,

                    chapter,

                    index,

                    previous_tail
                )


                if text:

                    script_parts.append(
                        text
                    )

                    previous_tail = (
                        text[-1000:]
                    )

                    print(
                        f"✅ Bölüm {index}: "
                        f"{len(text.split())} kelime"
                    )

                    success = True

                    break


                print(
                    f"⚠️ Bölüm {index} "
                    f"boş geldi."
                )


            except Exception as e:

                print(
                    f"⚠️ Bölüm {index} "
                    f"hata:",
                    str(e)
                )

                if retry < 2:
                    time.sleep(3)


        if not success:

            print(
                f"❌ Bölüm {index} "
                f"üretilemedi."
            )


    # =====================================================
    # SON KONTROL
    # =====================================================

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )


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

    print()
    print(
        "🏷️ YouTube metadata "
        "oluşturuluyor..."
    )


    metadata = generate_metadata(
        topic
    )


    # =====================================================
    # DOSYA
    # =====================================================

    final_content = (

        full_script

        + "\n\n"

        + METADATA_AYIRICI

        + "\n\n"

        + metadata
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
        "📁",
        OUTPUT_FILE
    )

    print(
        "🎯 Konu:",
        topic
    )

    print(
        "📝 Kelime:",
        total_words
    )

    print(
        "📚 Bölüm:",
        len(script_parts)
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()
