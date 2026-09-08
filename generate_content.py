import os
import sys
import json
import re
import time
import random
from datetime import datetime

import requests


# =========================================================
# DİZİNLER
# =========================================================

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

os.makedirs(OUT, exist_ok=True)


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
print("🔑 API KONTROLÜ")
print("================================")

if GEMINI_API_KEY:
    print("✅ GEMINI_API_KEY mevcut.")
else:
    print("⚠️ GEMINI_API_KEY bulunamadı.")

if CEREBRAS_API_KEY:
    print("✅ CEREBRAS_API_KEY mevcut.")
else:
    print("⚠️ CEREBRAS_API_KEY bulunamadı.")

if NVIDIA_API_KEY:
    print("✅ NVIDIA_API_KEY mevcut.")
else:
    print("⚠️ NVIDIA_API_KEY bulunamadı.")

print("================================")
print()


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
# API URL / MODEL
# =========================================================

# Gemini
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

# Cerebras
CEREBRAS_URL = (
    "https://api.cerebras.ai/v1/chat/completions"
)

CEREBRAS_MODEL = "llama-3.3-70b"

# NVIDIA
NVIDIA_URL = (
    "https://integrate.api.nvidia.com/v1/chat/completions"
)

# Eski:
# meta/llama-3.3-70b-instruct
#
# Bu model artık kullanılmıyor.
#
# Güncel NVIDIA endpoint'lerinden biri:
NVIDIA_MODEL = "deepseek-ai/deepseek-v4-flash-0731"


# =========================================================
# BELGESEL AYARLARI
# =========================================================

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100

METADATA_AYIRICI = "===METADATA_AYIRICI==="


# =========================================================
# ÖRNEK KONULAR
# =========================================================

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden dışlanması
- Nikola Tesla'nın hayatının son dönemindeki yalnızlığı
- Alan Turing'in savaşa katkısı ve sonrasında yaşadıkları
- Rosalind Franklin'in DNA araştırmalarındaki katkısı
- Marie Curie'nin radyasyon araştırmaları
- Ludwig Boltzmann'ın bilimsel fikirleri nedeniyle yaşadığı baskı
- Barbara McClintock'un yıllarca anlaşılmayan keşfi
- Galileo'nun bilimsel fikirleri nedeniyle yargılanması
- Giordano Bruno'nun fikirleri nedeniyle idam edilmesi
- Évariste Galois'nın kısa ama sıra dışı hayatı
- Vera Rubin'in karanlık madde araştırmaları
- Jocelyn Bell Burnell'in pulsar keşfi
- Emmy Noether'in akademide karşılaştığı engeller
- Ada Lovelace'in erken bilgisayar tarihindeki rolü
- Katherine Johnson'un NASA'daki bilimsel katkıları
- Srinivasa Ramanujan'ın matematiksel dehası
- Kurt Gödel'in son yılları
- Antoine Lavoisier'in bilimsel çalışmaları ve trajik sonu
"""


# =========================================================
# ANLATIM KURALLARI
# =========================================================

NARRATION_KURALLARI = """
KURALLAR:

1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Emin olunmayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı bir akışla anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Metin doğrudan TTS sistemine gönderilecek.
10. Doğal Türkçe cümleler kullan.

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

İzleyici bölümlere ayrıldığını fark etmemeli.

Anlatım kesintisiz tek bir belgesel akışı gibi
hissettirmeli.

Sadece seçilen konuyu doğrudan anlat.

Metin doğrudan TTS sistemine gönderileceği için
okuyucu yalnızca gerçek anlatım cümlelerini görmelidir.
"""


# =========================================================
# ORTAK YARDIMCI
# =========================================================

def print_response_error(provider, response):
    print()
    print("=" * 60)
    print(f"❌ {provider} API HATASI")
    print("=" * 60)
    print("HTTP:", response.status_code)

    try:
        body = response.text
        print(body[:4000])
    except Exception:
        print("(Hata gövdesi okunamadı.)")

    print("=" * 60)
    print()


def get_retry_after(response, default=5):
    value = response.headers.get("Retry-After")

    if value:
        try:
            return max(1, int(float(value)))
        except Exception:
            pass

    return default


# =========================================================
# GEMINI
# =========================================================

def call_gemini(prompt, max_retries=3):

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY bulunamadı.")
        return None

    for attempt in range(1, max_retries + 1):

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
                timeout=180
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            if response.ok:

                try:
                    data = response.json()

                    candidates = data.get(
                        "candidates",
                        []
                    )

                    if not candidates:
                        print(
                            "❌ Gemini candidates boş."
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

                    text_parts = []

                    for part in parts:
                        text = part.get("text")

                        if text:
                            text_parts.append(text)

                    result = "\n".join(
                        text_parts
                    ).strip()

                    if result:
                        return result

                    print(
                        "❌ Gemini boş cevap verdi."
                    )
                    return None

                except Exception as e:
                    print(
                        "❌ Gemini JSON işleme hatası:",
                        type(e).__name__,
                        str(e)
                    )
                    return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429 / kota veya hız limiti."
                )

                if attempt >= max_retries:
                    print(
                        "⚠️ Gemini retry limiti doldu."
                    )
                    return None

                wait_time = get_retry_after(
                    response,
                    default=10 * attempt
                )

                # Bir miktar jitter
                wait_time += random.randint(0, 3)

                print(
                    f"⏳ Gemini için "
                    f"{wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)
                continue

            # -------------------------------------------------
            # Sunucu hataları
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                print(
                    "⚠️ Gemini sunucu hatası."
                )

                if attempt >= max_retries:
                    return None

                wait_time = (
                    5 * attempt
                    + random.randint(0, 3)
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)
                continue

            # -------------------------------------------------
            # Diğer hatalar
            # -------------------------------------------------

            print_response_error(
                "GEMINI",
                response
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt >= max_retries:
                return None

            time.sleep(5)

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini ağ hatası:",
                str(e)
            )

            if attempt >= max_retries:
                return None

            time.sleep(5)

    return None


# =========================================================
# CEREBRAS
# =========================================================

def call_cerebras(prompt, max_retries=2):

    if not CEREBRAS_API_KEY:
        print(
            "❌ CEREBRAS_API_KEY bulunamadı."
        )
        return None

    headers = {
        "Authorization": (
            f"Bearer {CEREBRAS_API_KEY}"
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "model": CEREBRAS_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen profesyonel Türkçe "
                    "tarih ve bilim belgeseli "
                    "yazarı olarak görev yapıyorsun."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 12000
    }

    for attempt in range(1, max_retries + 1):

        print(
            f"🟢 Cerebras isteği "
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

                try:

                    data = response.json()

                    choices = data.get(
                        "choices",
                        []
                    )

                    if not choices:
                        print(
                            "❌ Cerebras choices boş."
                        )
                        return None

                    message = choices[0].get(
                        "message",
                        {}
                    )

                    result = message.get(
                        "content",
                        ""
                    )

                    if result:
                        return result.strip()

                    print(
                        "❌ Cerebras boş cevap verdi."
                    )
                    return None

                except Exception as e:

                    print(
                        "❌ Cerebras JSON işleme hatası:",
                        type(e).__name__,
                        str(e)
                    )

                    return None

            # -------------------------------------------------
            # 401
            # -------------------------------------------------

            if response.status_code == 401:

                print(
                    "❌ Cerebras API key geçersiz."
                )

                print(
                    "ℹ️ GitHub Secrets içindeki "
                    "CEREBRAS_API_KEY kontrol edilmeli."
                )

                # 401 için tekrar denemek anlamsız.
                return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Cerebras 429 / kota."
                )

                if attempt >= max_retries:
                    return None

                wait_time = get_retry_after(
                    response,
                    default=10 * attempt
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)
                continue

            # -------------------------------------------------
            # Sunucu hataları
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt >= max_retries:
                    return None

                wait_time = 5 * attempt

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)
                continue

            print_response_error(
                "CEREBRAS",
                response
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ Cerebras timeout."
            )

            if attempt >= max_retries:
                return None

            time.sleep(5)

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Cerebras ağ hatası:",
                str(e)
            )

            if attempt >= max_retries:
                return None

            time.sleep(5)

    return None


# =========================================================
# NVIDIA
# =========================================================

def call_nvidia(prompt, max_retries=2):

    if not NVIDIA_API_KEY:
        print(
            "❌ NVIDIA_API_KEY bulunamadı."
        )
        return None

    headers = {
        "Authorization": (
            f"Bearer {NVIDIA_API_KEY}"
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen profesyonel Türkçe "
                    "tarih ve bilim belgeseli "
                    "yazarı olarak görev yapıyorsun."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 12000
    }

    for attempt in range(1, max_retries + 1):

        print(
            f"🟩 NVIDIA isteği "
            f"{attempt}/{max_retries}"
        )

        try:

            response = requests.post(
                NVIDIA_URL,
                headers=headers,
                json=payload,
                timeout=180
            )

            print(
                "NVIDIA HTTP:",
                response.status_code
            )

            if response.ok:

                try:

                    data = response.json()

                    choices = data.get(
                        "choices",
                        []
                    )

                    if not choices:
                        print(
                            "❌ NVIDIA choices boş."
                        )
                        return None

                    message = choices[0].get(
                        "message",
                        {}
                    )

                    result = message.get(
                        "content",
                        ""
                    )

                    if result:
                        return result.strip()

                    print(
                        "❌ NVIDIA boş cevap verdi."
                    )
                    return None

                except Exception as e:

                    print(
                        "❌ NVIDIA JSON işleme hatası:",
                        type(e).__name__,
                        str(e)
                    )

                    return None

            # -------------------------------------------------
            # 401
            # -------------------------------------------------

            if response.status_code == 401:

                print(
                    "❌ NVIDIA API key geçersiz."
                )

                return None

            # -------------------------------------------------
            # 404 / 410
            # -------------------------------------------------

            if response.status_code in {
                404,
                410
            }:

                print(
                    "❌ NVIDIA modeli kullanılamıyor."
                )

                print(
                    "Model:",
                    NVIDIA_MODEL
                )

                print_response_error(
                    "NVIDIA",
                    response
                )

                # Model yoksa retry anlamsız.
                return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ NVIDIA 429 / kota."
                )

                if attempt >= max_retries:
                    return None

                wait_time = get_retry_after(
                    response,
                    default=10 * attempt
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)
                continue

            # -------------------------------------------------
            # Sunucu hataları
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt >= max_retries:
                    return None

                wait_time = 5 * attempt

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)
                continue

            print_response_error(
                "NVIDIA",
                response
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ NVIDIA timeout."
            )

            if attempt >= max_retries:
                return None

            time.sleep(5)

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ NVIDIA ağ hatası:",
                str(e)
            )

            if attempt >= max_retries:
                return None

            time.sleep(5)

    return None


# =========================================================
# ANA AI FALLBACK
# =========================================================

def call_ai(prompt):

    # =====================================================
    # 1. GEMINI
    # =====================================================

    if GEMINI_API_KEY:

        result = call_gemini(
            prompt,
            max_retries=3
        )

        if result:

            print()
            print(
                "✅ İçerik Gemini "
                "tarafından üretildi."
            )

            return result

    print()
    print("================================")
    print("⚠️ GEMINI BAŞARISIZ")
    print("🟢 CEREBRAS YEDEK SİSTEM DEVREDE")
    print("================================")

    # =====================================================
    # 2. CEREBRAS
    # =====================================================

    if CEREBRAS_API_KEY:

        result = call_cerebras(
            prompt,
            max_retries=2
        )

        if result:

            print()
            print(
                "✅ İçerik Cerebras "
                "tarafından üretildi."
            )

            return result

    else:

        print(
            "⚠️ Cerebras API key yok, "
            "NVIDIA'ya geçiliyor."
        )

    print()
    print("================================")
    print("⚠️ CEREBRAS DA BAŞARISIZ")
    print("🟩 NVIDIA YEDEK SİSTEM DEVREDE")
    print("================================")

    # =====================================================
    # 3. NVIDIA
    # =====================================================

    if NVIDIA_API_KEY:

        result = call_nvidia(
            prompt,
            max_retries=2
        )

        if result:

            print()
            print(
                "✅ İçerik NVIDIA "
                "tarafından üretildi."
            )

            return result

    else:

        print(
            "⚠️ NVIDIA API key yok."
        )

    raise SystemExit(
        "❌ Gemini, Cerebras ve NVIDIA "
        "başarısız oldu."
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

            return []

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

    if not re.search(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}",
        topic
    ):
        return False

    if len(topic.split()) < 2:
        return False

    return True


# =========================================================
# KONU + PLAN
# =========================================================

def generate_topic_and_outline(history):

    if history:

        avoid_list = "\n".join(
            f"- {t}"
            for t in history
        )

    else:

        avoid_list = "(henüz yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
bilgi/tarih/bilim YouTube kanalı için
30-45 dakikalık belgesel hazırlayan
profesyonel editör ve senaristsin.

KANALIN NİŞİ:

Kanal bilim insanlarının, mucitlerin ve
kaşiflerin İNSANİ VE DRAMATİK HİKAYELERİNE
odaklanıyor.

Kuru bilgi anlatımı istemiyorum.

Bir bilim insanının yaşadığı:

haksızlık,
trajedi,
mücadele,
yalnızlık,
başarısızlık,
geç kabul görme,
bilimsel engeller,
toplumsal baskı

gibi gerçek olaylardan hareketle güçlü
bir belgesel konusu seç.

Amaç izleyicide gerçek bir duygusal bağ
oluşturmak.

ÖRNEK KONULAR:

{ORNEK_KONULAR}

Daha önce kullanılan konular:

{avoid_list}

Bu istekte:

1. Tek bir konu seç.
2. Konu için 5 bölümlük plan oluştur.

Her bölüm yaklaşık
{BOLUM_BASINA_KELIME} kelimelik anlatımı
destekleyecek kadar zengin olmalıdır.

Toplam hedef:

{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime.

KURALLAR:

- Gerçek ve doğrulanabilir konu seç.
- Bilgi uydurma.
- Diktatör veya savaş suçlusu seçme.
- Propaganda üretme.
- Kışkırtıcı siyasi içerik üretme.
- Sadece bilim insanı, mucit veya kaşif seç.
- Kişinin insani tarafını merkeze al.
- Güçlü açılış düşün.
- Son bölüm güçlü kapanışa sahip olsun.
- Markdown kullanma.

ÇIKTI FORMATI:

KONU: <konu>
BÖLÜM 1: <başlık> - <özet>
BÖLÜM 2: <başlık> - <özet>
BÖLÜM 3: <başlık> - <özet>
BÖLÜM 4: <başlık> - <özet>
BÖLÜM 5: <başlık> - <özet>
"""

    raw = call_ai(prompt)

    if not raw:
        return "", []

    topic = ""
    bolumler = []

    for line in raw.strip().splitlines():

        line = line.strip()

        if not line:
            continue

        clean_line = (
            line
            .replace("*", "")
            .replace("#", "")
            .strip()
        )

        upper = clean_line.upper()

        if upper.startswith("KONU:"):

            topic = (
                clean_line
                .split(":", 1)[1]
                .strip()
            )

        elif (
            upper.startswith("BÖLÜM")
            or upper.startswith("BOLUM")
        ):

            bolumler.append(
                clean_line
            )

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip().strip('"').strip()

    # AI sadece konu verdiyse
    if not bolumler and topic:

        bolumler = [
            f"BÖLÜM 1: {topic} - Konunun genel anlatımı"
        ]

    print()
    print(
        "---- AI HAM ÇIKTI ----"
    )

    print(
        raw[:2500]
    )

    print(
        "---- ÜRETİLEN KONU:",
        repr(topic)
    )

    print(
        "---- BÖLÜM SAYISI:",
        len(bolumler)
    )

    print(
        "----------------------"
    )

    return topic, bolumler


# =========================================================
# BÖLÜM ÜRETİMİ
# =========================================================

def generate_chapter(
    topic,
    outline_text,
    chapter_line,
    chapter_index,
    total_chapters,
    previous_tail,
    need_metadata
):

    devamlilik = ""

    if previous_tail:

        devamlilik = f"""

BİR ÖNCEKİ BÖLÜMÜN SON KISMI:

\"\"\"
{previous_tail}
\"\"\"

Buradan doğal şekilde devam et.

Önceki kısmı tekrar etme.
"""


    metadata_talimati = ""

    if need_metadata:

        metadata_talimati = f"""

BU SON BÖLÜM.

Anlatımı bitirdikten sonra aşağıdaki
ayırıcıyı kullan:

{METADATA_AYIRICI}

BAŞLIK:
Merak uyandırıcı ama yanıltıcı olmayan
YouTube başlığı.

AÇIKLAMA:
3-5 cümlelik açıklama.

ETİKETLER:
15-25 Türkçe etiket,
virgülle ayrılmış.
"""


    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı
için profesyonel Türkçe tarih ve bilim
belgeseli anlatıcısısın.

Kanalın nişi:

Bilim insanlarının, mucitlerin ve kaşiflerin
insani ve dramatik hikayeleri.

GENEL KONU:

{topic}

BÖLÜM PLANI:

{outline_text}

YAZILACAK BÖLÜM:

{chapter_line}

{devamlilik}

Yaklaşık
{BOLUM_BASINA_KELIME}
kelimelik akıcı ve kesintisiz
belgesel anlatımı yaz.

Bu bölümün başlangıcı ve bitişi,
genel hikayenin doğal parçası gibi olsun.

İzleyici bunun bir bölüm olduğunu
fark etmemeli.

Anlatım:

- ciddi
- doğal
- profesyonel
- merak uyandırıcı
- duygusal ama abartısız

olmalı.

{NARRATION_KURALLARI}

ÇIKTI SADECE SESLENDİRME METNİ OLMALI.

Başlık yazma.
Bölüm numarası yazma.
Sahne açıklaması yazma.
Kamera açıklaması yazma.
Müzik açıklaması yazma.

{metadata_talimati}
"""

    raw = call_ai(prompt)

    if not raw:
        return ""

    return raw.strip()


# =========================================================
# METADATA AYIRMA
# =========================================================

def parse_chapter_with_metadata(raw_text):

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


# =========================================================
# VARSAYILAN METADATA
# =========================================================

def default_metadata(topic):

    return (
        "BAŞLIK:\n"
        f"{topic[:95]}\n\n"
        "AÇIKLAMA:\n"
        f"{topic} hakkında kapsamlı "
        "bir belgesel.\n\n"
        "ETİKETLER:\n"
        "tarih, bilim, belgesel, keşif, "
        "bilgi, bilim insanları"
    )


# =========================================================
# ANA
# =========================================================

def main():

    print("================================")
    print(
        "🎬 30-45 DAKİKALIK "
        "BELGESEL MOTORU"
    )
    print("================================")

    print(
        f"Hedef: "
        f"{BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )

    print(
        f"Toplam hedef: "
        f"{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime"
    )

    print(
        "Ana AI: Gemini"
    )

    print(
        "1. Yedek AI: Cerebras"
    )

    print(
        "2. Yedek AI: NVIDIA"
    )

    print()

    history = load_history()

    topic = None
    bolumler = None

    # =====================================================
    # KONU ÜRETİMİ
    # =====================================================

    print(
        "🧭 Konu + bölüm planı oluşturuluyor..."
    )

    for attempt in range(1, 3):

        try:

            print(
                f"🔄 Konu denemesi "
                f"{attempt}/2"
            )

            candidate_topic, candidate_bolumler = (
                generate_topic_and_outline(
                    history
                )
            )

            if (
                candidate_topic
                and is_valid_topic(
                    candidate_topic
                )
                and candidate_topic not in history
                and candidate_bolumler
            ):

                topic = candidate_topic
                bolumler = candidate_bolumler

                break

            print(
                "⚠️ Geçersiz veya tekrar konu."
            )

        except SystemExit:
            raise

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                type(e).__name__,
                str(e)
            )

            if attempt < 2:
                time.sleep(5)

    if not topic:

        raise SystemExit(
            "❌ Geçerli konu üretilemedi."
        )

    # =====================================================
    # BÖLÜM SAYISINI SINIRLA
    # =====================================================

    bolumler = bolumler[
        :BOLUM_SAYISI
    ]

    outline_text = "\n".join(
        bolumler
    )

    print()
    print(
        "🎯 Konu:",
        topic
    )

    for b in bolumler:

        print(
            "  -",
            b
        )

    # =====================================================
    # GEÇMİŞE EKLE
    # =====================================================

    if topic not in history:

        history.append(topic)

        # Aşırı büyümeyi engelle
        history = history[-200:]

        save_history(history)

    # =====================================================
    # KONU DOSYASI
    # =====================================================

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(topic)

    print()
    print(
        "✍️ Bölümler yazılıyor..."
    )

    # =====================================================
    # BÖLÜMLER
    # =====================================================

    script_parts = []

    previous_tail = None

    metadata_raw = None

    total = len(
        bolumler
    )

    for idx, chapter_line in enumerate(
        bolumler,
        1
    ):

        is_last = (
            idx == total
        )

        print()
        print(
            "================================"
        )

        print(
            f"📝 Bölüm "
            f"{idx}/{total}"
        )

        print(
            "================================"
        )

        try:

            raw = generate_chapter(
                topic=topic,
                outline_text=outline_text,
                chapter_line=chapter_line,
                chapter_index=idx,
                total_chapters=total,
                previous_tail=previous_tail,
                need_metadata=is_last
            )

        except SystemExit:

            raise

        except Exception as e:

            print(
                f"❌ Bölüm {idx} üretim hatası:"
            )

            print(
                type(e).__name__,
                str(e)
            )

            raw = ""

        chapter_text, maybe_metadata = (
            parse_chapter_with_metadata(
                raw
            )
        )

        if not chapter_text:

            print(
                f"⚠️ Bölüm {idx} boş geldi."
            )

            continue

        script_parts.append(
            chapter_text
        )

        previous_tail = (
            chapter_text[-700:]
        )

        if is_last:
            metadata_raw = (
                maybe_metadata
            )

        print(
            f"✅ Bölüm {idx}: "
            f"{len(chapter_text.split())} kelime"
        )

    # =====================================================
    # SONUÇ
    # =====================================================

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )

    full_script = "\n\n".join(
        script_parts
    )

    toplam_kelime = len(
        full_script.split()
    )

    print()
    print(
        "================================"
    )

    print(
        f"📊 Toplam kelime: "
        f"{toplam_kelime}"
    )

    print(
        "================================"
    )

    # =====================================================
    # METADATA
    # =====================================================

    if metadata_raw:

        metadata_text = (
            metadata_raw.strip()
        )

    else:

        print(
            "⚠️ Metadata üretilemedi."
        )

        print(
            "ℹ️ Varsayılan metadata kullanılıyor."
        )

        metadata_text = (
            default_metadata(
                topic
            )
        )

    # =====================================================
    # DOSYAYI OLUŞTUR
    # =====================================================

    final_content = (
        full_script
        + "\n\n"
        + METADATA_AYIRICI
        + "\n\n"
        + metadata_text
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            final_content
        )

    # =====================================================
    # SON
    # =====================================================

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
        "📝 Kelime sayısı:",
        toplam_kelime
    )

    print(
        "🎯 Konu:",
        topic
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "❌ İşlem kullanıcı tarafından "
            "durduruldu."
        )

        sys.exit(1)

    except SystemExit:

        raise

    except Exception as e:

        print()
        print(
            "================================"
        )

        print(
            "❌ BEKLENMEYEN ANA HATA"
        )

        print(
            "================================"
        )

        print(
            "Hata türü:",
            type(e).__name__
        )

        print(
            "Hata:",
            str(e)
        )

        print(
            "================================"
        )

        sys.exit(1)
