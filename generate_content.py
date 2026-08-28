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
# API KEYLER
# GitHub Actions Secrets üzerinden alınır.
# Keyleri bu dosyaya kesinlikle yazma.
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY bulunamadı.")

if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY bulunamadı.")

# ============================================================
# DOSYALAR
# ============================================================

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(
    REPO_BASE,
    "video_topic_history.json"
)
OUTPUT_FILE = os.path.join(
    OUT,
    "current_content.txt"
)

# ============================================================
# API AYARLARI
# ============================================================

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_MODEL = "openai/gpt-oss-120b"

# ============================================================
# VİDEO AYARLARI
# ============================================================

MAX_HISTORY = 30

BOLUM_SAYISI = 2
BOLUM_BASINA_KELIME = 1500

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# ============================================================
# ANLATIM KURALLARI
# ============================================================

NARRATION_KURALLARI = """
KURALLAR:

1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Doğrulanamayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı bir akışla anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Metin doğrudan TTS sistemine gönderilecek.

ÖNEMLİ:

Bu bir film senaryosu değildir.

Sahne yazma.
Kamera hareketi yazma.
Karakter hareketi yazma.
Müzik yazma.
Ses efekti yazma.

Parantez veya köşeli parantez kullanma.

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

# ============================================================
# GEMINI
# ============================================================

def call_gemini(prompt, max_retries=3):

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY bulunamadı.")
        return None

    retry_statuses = {
        500,
        502,
        503,
        504
    }

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
                    ]
                },
                timeout=180
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            # ------------------------------------------------
            # BAŞARILI
            # ------------------------------------------------

            if response.ok:

                try:

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

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):

                    print(
                        "❌ Gemini cevabı "
                        "beklenen formatta değil."
                    )

                    return None

            # ------------------------------------------------
            # 429 KOTA
            # ------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429 / kota hatası."
                )

                print(
                    "🔄 Groq'a geçilecek."
                )

                return None

            # ------------------------------------------------
            # SUNUCU HATALARI
            # ------------------------------------------------

            if response.status_code in retry_statuses:

                if attempt >= max_retries:

                    print(
                        "❌ Gemini sunucu hatası."
                    )

                    return None

                wait_time = (
                    10 *
                    (2 ** (attempt - 1))
                    +
                    random.randint(
                        0,
                        5
                    )
                )

                print(
                    f"⏳ {wait_time} saniye "
                    "sonra Gemini tekrar denenecek..."
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
                response.text[:2000]
            )

            return None

        except requests.exceptions.Timeout:

            if attempt >= max_retries:

                print(
                    "❌ Gemini timeout."
                )

                return None

            wait_time = (
                10 * attempt
            )

            print(
                f"⚠️ Timeout. "
                f"{wait_time} saniye bekleniyor."
            )

            time.sleep(
                wait_time
            )

        except requests.exceptions.RequestException as e:

            if attempt >= max_retries:

                print(
                    "❌ Gemini ağ hatası:",
                    str(e)
                )

                return None

            wait_time = (
                10 * attempt
            )

            print(
                f"⚠️ Ağ hatası. "
                f"{wait_time} saniye bekleniyor."
            )

            time.sleep(
                wait_time
            )

    return None


# ============================================================
# GROQ
# ============================================================

def call_groq(prompt, max_retries=3):

    if not GROQ_API_KEY:

        print(
            "❌ GROQ_API_KEY bulunamadı."
        )

        print(
            "⚠️ GitHub Secrets bölümünde "
            "GROQ_API_KEY oluştur."
        )

        return None

    # Key'de yanlışlıkla satır sonu / boşluk varsa temizle
    api_key = GROQ_API_KEY.strip()

    headers = {
        "Authorization": (
            f"Bearer {api_key}"
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
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

    for attempt in range(
        1,
        max_retries + 1
    ):

        print(
            f"🟢 Groq isteği "
            f"{attempt}/{max_retries}"
        )

        try:

            response = requests.post(
                GROQ_URL,
                headers=headers,
                json=payload,
                timeout=180
            )

            print(
                "Groq HTTP:",
                response.status_code
            )

            # ------------------------------------------------
            # BAŞARILI
            # ------------------------------------------------

            if response.ok:

                try:

                    data = response.json()

                    return (
                        data[
                            "choices"
                        ][0][
                            "message"
                        ][
                            "content"
                        ]
                    )

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):

                    print(
                        "❌ Groq cevabı "
                        "beklenen formatta değil."
                    )

                    return None

            # ------------------------------------------------
            # 401 API KEY
            # ------------------------------------------------

            if response.status_code == 401:

                print(
                    "❌ Groq API key geçersiz."
                )

                print(
                    "⚠️ GitHub Secrets bölümündeki "
                    "GROQ_API_KEY değerini kontrol et."
                )

                print(
                    "⚠️ Key Python dosyasına değil, "
                    "GitHub Secret'a yazılmalı."
                )

                return None

            # ------------------------------------------------
            # 429 KOTA
            # ------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Groq 429 / kota hatası."
                )

                if attempt >= max_retries:

                    return None

                wait_time = (
                    15 * attempt
                )

                print(
                    f"⏳ {wait_time} saniye "
                    "bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue

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
                        "❌ Groq sunucu hatası."
                    )

                    return None

                wait_time = (
                    10 * attempt
                )

                print(
                    f"⏳ {wait_time} saniye "
                    "bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # ------------------------------------------------
            # DİĞER HATALAR
            # ------------------------------------------------

            print(
                "❌ Groq kalıcı hata:"
            )

            print(
                response.text[:2000]
            )

            return None

        except requests.exceptions.Timeout:

            if attempt >= max_retries:

                print(
                    "❌ Groq timeout."
                )

                return None

            wait_time = (
                10 * attempt
            )

            print(
                f"⚠️ Groq timeout. "
                f"{wait_time} saniye bekleniyor."
            )

            time.sleep(
                wait_time
            )

        except requests.exceptions.RequestException as e:

            if attempt >= max_retries:

                print(
                    "❌ Groq ağ hatası:",
                    str(e)
                )

                return None

            wait_time = (
                10 * attempt
            )

            print(
                f"⚠️ Groq ağ hatası. "
                f"{wait_time} saniye bekleniyor."
            )

            time.sleep(
                wait_time
            )

    return None


# ============================================================
# AI SEÇİMİ
# ============================================================

def call_ai(prompt):

    # --------------------------------------------------------
    # 1. GEMINI
    # --------------------------------------------------------

    if GEMINI_API_KEY:

        result = call_gemini(
            prompt
        )

        if result:

            print(
                "✅ İçerik Gemini "
                "tarafından üretildi."
            )

            return result

    # --------------------------------------------------------
    # 2. GROQ YEDEK
    # --------------------------------------------------------

    print()
    print(
        "================================"
    )
    print(
        "⚠️ GEMINI BAŞARISIZ"
    )
    print(
        "🟢 GROQ YEDEK SİSTEM DEVREDE"
    )
    print(
        "================================"
    )

    result = call_groq(
        prompt
    )

    if result:

        print(
            "✅ İçerik Groq "
            "tarafından üretildi."
        )

        return result

    raise SystemExit(
        "❌ Gemini ve Groq başarısız oldu."
    )


# ============================================================
# GEÇMİŞ
# ============================================================

def load_history():

    if os.path.exists(
        TOPIC_HISTORY_FILE
    ):

        try:

            with open(
                TOPIC_HISTORY_FILE,
                encoding="utf-8"
            ) as f:

                data = json.load(f)

                if isinstance(
                    data,
                    list
                ):

                    return data

                return []

        except Exception:

            return []

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

    if len(topic) < 8:

        return False

    if len(topic) > 220:

        return False

    if not re.search(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}",
        topic
    ):

        return False

    if len(
        topic.split()
    ) < 2:

        return False

    return True


# ============================================================
# KONU + BÖLÜM PLANI
# ============================================================

def generate_topic_and_outline(history):

    avoid_list = (
        "\n".join(
            f"- {t}"
            for t in history
        )
        if history
        else "(henüz yok)"
    )

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı
Türkçe bilgi/tarih/bilim YouTube kanalı
için yaklaşık 20 dakikalık belgesel
hazırlayan editör ve senaristsin.

Bu istekte HEM konuyu seç
HEM bölüm planını oluştur.

SEÇİLEN KONU yaklaşık 20 dakikalık
anlatımı doldurabilecek kadar zengin olmalı.

Daha önce kullanılan konular:

{avoid_list}

Konuyu {BOLUM_SAYISI} bölümde anlat.

Her bölüm yaklaşık
{BOLUM_BASINA_KELIME} kelime olsun.

Toplam yaklaşık
3000 kelimelik bir belgesel oluştur.

KURALLAR:

- Güçlü açılış ve merak unsuru kullan.
- Son bölüm güçlü bir kapanışla bitsin.
- Konu tekrarı yapma.
- Gerçek ve doğrulanabilir konu seç.
- Diktatör veya savaş suçlusu önerme.
- Propaganda veya kışkırtıcı içerik üretme.

ÇIKTI FORMATI TAM OLARAK ŞU ŞEKİLDE OLSUN:

KONU: <konu>

BÖLÜM 1: <başlık> - <özet>

BÖLÜM 2: <başlık> - <özet>
"""

    raw = call_ai(
        prompt
    )

    if not raw:

        return "", []

    topic = ""
    bolumler = []

    # --------------------------------------------------------
    # CEVABI SATIR SATIR OKU
    # --------------------------------------------------------

    for line in raw.strip().splitlines():

        line = line.strip()

        if not line:

            continue

        upper_line = line.upper()

        # KONU
        if upper_line.startswith(
            "KONU:"
        ):

            topic = (
                line.split(
                    ":",
                    1
                )[1]
                .strip()
            )

        # BÖLÜM
        elif (
            upper_line.startswith(
                "BÖLÜM"
            )
            or
            upper_line.startswith(
                "BOLUM"
            )
        ):

            bolumler.append(
                line
            )

    # --------------------------------------------------------
    # KONU TEMİZLE
    # --------------------------------------------------------

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip()

    topic = topic.strip(
        '"'
    ).strip()

    # --------------------------------------------------------
    # EĞER KONU BULUNDU AMA BÖLÜM YOKSA
    # --------------------------------------------------------

    if (
        not bolumler
        and topic
    ):

        bolumler = [
            (
                f"BÖLÜM 1: "
                f"{topic} - "
                f"Konunun genel anlatımı"
            )
        ]

    return topic, bolumler


# ============================================================
# BÖLÜM ÜRET
# ============================================================

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

Tekrar yapma.
Aynı bilgileri yeniden anlatma.
"""


    metadata_talimati = ""

    if need_metadata:

        metadata_talimati = f"""
BU SON BÖLÜM.

Metni bitirdikten sonra şu ayırıcıyı kullan:

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
Sen DAHİLER VE KEŞİFLER adlı
YouTube kanalı için profesyonel
Türkçe tarih/bilim belgeseli anlatıcısısın.

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

İzleyici bunun bir bölüm olduğunu
fark etmemeli.

{NARRATION_KURALLARI}

ÇIKTI SADECE SESLENDİRME METNİ OLMALI.

Başlık yazma.
Bölüm numarası yazma.
Sahne açıklaması yazma.

{metadata_talimati}
"""

    raw = call_ai(
        prompt
    )

    if not raw:

        return ""

    return raw.strip()


# ============================================================
# METADATA AYIR
# ============================================================

def parse_chapter_with_metadata(
    raw_text
):

    if (
        METADATA_AYIRICI
        in raw_text
    ):

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
# YEDEK METADATA
# ============================================================

def default_metadata(topic):

    return (
        f"BAŞLIK:\n"
        f"{topic[:95]}\n\n"

        f"AÇIKLAMA:\n"
        f"{topic} hakkında kapsamlı "
        f"bir belgesel.\n\n"

        f"ETİKETLER:\n"
        f"tarih, bilim, belgesel, "
        f"keşif, bilgi"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "================================"
    )

    print(
        "🎬 20 DAKİKALIK "
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
        f"{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime"
    )

    print(
        "Ana AI: Gemini"
    )

    print(
        "Yedek AI: Groq GPT-OSS 120B"
    )

    print()

    # --------------------------------------------------------
    # GEÇMİŞİ YÜKLE
    # --------------------------------------------------------

    history = load_history()

    topic = None
    bolumler = None

    print(
        "🧭 Konu + bölüm planı oluşturuluyor..."
    )

    # --------------------------------------------------------
    # KONU ÜRET
    # --------------------------------------------------------

    for attempt in range(2):

        try:

            (
                candidate_topic,
                candidate_bolumler
            ) = generate_topic_and_outline(
                history
            )

            # ------------------------------------------------
            # KONU GEÇERLİ
            # ------------------------------------------------

            if (
                candidate_topic
                and
                is_valid_topic(
                    candidate_topic
                )
                and
                candidate_topic not in history
                and
                candidate_bolumler
            ):

                topic = candidate_topic

                bolumler = (
                    candidate_bolumler
                )

                break

            print(
                "⚠️ Geçersiz veya "
                "tekrar konu."
            )

            print(
                "AI cevabı:",
                repr(
                    candidate_topic
                )
            )

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 1:

                time.sleep(
                    5
                )

    # --------------------------------------------------------
    # KONU BULUNAMADI
    # --------------------------------------------------------

    if not topic:

        raise SystemExit(
            "❌ Geçerli konu üretilemedi."
        )

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

    # --------------------------------------------------------
    # GEÇMİŞE EKLE
    # --------------------------------------------------------

    history.append(
        topic
    )

    save_history(
        history
    )

    # --------------------------------------------------------
    # OUTPUT KLASÖRÜ
    # --------------------------------------------------------

    os.makedirs(
        OUT,
        exist_ok=True
    )

    # --------------------------------------------------------
    # CURRENT TOPIC
    # --------------------------------------------------------

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            topic
        )

    # --------------------------------------------------------
    # BÖLÜMLER
    # --------------------------------------------------------

    print()

    print(
        "✍️ Bölümler yazılıyor..."
    )

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
            f"📝 Bölüm "
            f"{idx}/{total}"
        )

        raw = generate_chapter(
            topic=topic,
            outline_text=outline_text,
            chapter_line=chapter_line,
            chapter_index=idx,
            total_chapters=total,
            previous_tail=previous_tail,
            need_metadata=is_last
        )

        chapter_text, maybe_metadata = (
            parse_chapter_with_metadata(
                raw
            )
        )

        # ----------------------------------------------------
        # BOŞ BÖLÜM
        # ----------------------------------------------------

        if not chapter_text:

            print(
                f"⚠️ Bölüm {idx} "
                f"boş geldi."
            )

            continue

        # ----------------------------------------------------
        # BÖLÜMÜ EKLE
        # ----------------------------------------------------

        script_parts.append(
            chapter_text
        )

        # ----------------------------------------------------
        # DEVAMLILIK İÇİN SON 500 KARAKTER
        # ----------------------------------------------------

        previous_tail = (
            chapter_text[-500:]
        )

        # ----------------------------------------------------
        # METADATA
        # ----------------------------------------------------

        if is_last:

            metadata_raw = (
                maybe_metadata
            )

        print(
            f"✅ Bölüm {idx}: "
            f"{len(chapter_text.split())} kelime"
        )

    # --------------------------------------------------------
    # HİÇBİR BÖLÜM YOK
    # --------------------------------------------------------

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )

    # --------------------------------------------------------
    # TAM METİN
    # --------------------------------------------------------

    full_script = (
        "\n\n".join(
            script_parts
        )
    )

    # --------------------------------------------------------
    # KELİME SAYISI
    # --------------------------------------------------------

    toplam_kelime = len(
        full_script.split()
    )

    # --------------------------------------------------------
    # TAHMİNİ SÜRE
    # --------------------------------------------------------

    tahmini_dakika = round(
        toplam_kelime / 150
    )

    print()

    print(
        f"📊 Toplam: "
        f"{toplam_kelime} kelime"
    )

    print(
        f"⏱️ Tahmini süre: "
        f"{tahmini_dakika} dakika"
    )

    # --------------------------------------------------------
    # METADATA YOKSA YEDEK OLUŞTUR
    # --------------------------------------------------------

    if not metadata_raw:

        metadata_raw = (
            default_metadata(
                topic
            )
        )

    # --------------------------------------------------------
    # SON DOSYA
    # --------------------------------------------------------

    final_text = (
        "=== SESLENDİRME METNİ ===\n"
        + full_script
        + "\n\n=== METADATA ===\n"
        + metadata_raw
    )

    # --------------------------------------------------------
    # DOSYAYA YAZ
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            final_text
        )

    # --------------------------------------------------------
    # TAMAMLANDI
    # --------------------------------------------------------

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
        "Konu:",
        topic
    )

    print(
        "Toplam kelime:",
        toplam_kelime
    )

    print(
        "Tahmini dakika:",
        tahmini_dakika
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
