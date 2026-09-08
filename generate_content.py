import os
import sys
import json
import requests
import re
import time
import random

# =========================================================
# DİZİNLER
# =========================================================

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

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
# GEMINI
# =========================================================

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    ""
).strip()

GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent"
)

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY bulunamadı.")
    raise SystemExit(1)

print("================================")
print("✅ GEMINI_API_KEY mevcut.")
print("================================")

# =========================================================
# BELGESEL AYARLARI
# =========================================================

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100

TOPLAM_HEDEF = (
    BOLUM_SAYISI *
    BOLUM_BASINA_KELIME
)

METADATA_AYIRICI = (
    "===METADATA_AYIRICI==="
)

# =========================================================
# ÖRNEK KONULAR
# =========================================================

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden dışlanması
- Nikola Tesla'nın son yılları ve yalnızlığı
- Alan Turing'in savaşa katkısı ve trajik hayatı
- Rosalind Franklin'in DNA araştırmalarındaki payı
- Marie Curie'nin radyasyon araştırmaları
- Ludwig Boltzmann'ın bilim dünyasındaki mücadelesi
- Barbara McClintock'un keşfinin geç kabul edilmesi
- Galileo'nun bilimsel fikirleri nedeniyle yargılanması
- Giordano Bruno'nun fikirleri nedeniyle idam edilmesi
- Évariste Galois'nın kısa ve trajik hayatı
- Vera Rubin'in karanlık madde araştırmaları
- Jocelyn Bell Burnell'in pulsar keşfi
- Emmy Noether'in akademide yaşadığı engeller
- Ada Lovelace'in erken bilgisayar tarihindeki rolü
- Katherine Johnson'un NASA'daki bilimsel mücadelesi
- Srinivasa Ramanujan'ın sıra dışı matematik hayatı
- Kurt Gödel'in son yılları
- Antoine Lavoisier'nin bilimsel çalışmaları ve idamı
"""

# =========================================================
# ANLATIM KURALLARI
# =========================================================

NARRATION_KURALLARI = """
KURALLAR:

1. Bilgi uydurma.

2. Tarihleri, isimleri ve olayları mümkün olduğunca
doğru aktar.

3. Emin olunmayan bilgileri kesin gerçek gibi sunma.

4. Doğal, ciddi ve profesyonel Türkçe belgesel
anlatımı kullan.

5. Gereksiz tekrar yapma.

6. Konuyu kronolojik ve mantıklı bir akışla anlat.

7. Bilimsel konuları herkesin anlayabileceği
şekilde açıkla.

8. Önemli kişiler, tarihler, yerler ve olaylara
yer ver.

9. Metin doğrudan TTS sistemine gönderilecektir.

10. Film senaryosu yazma.

11. Sahne yazma.

12. Kamera hareketi yazma.

13. Müzik veya ses efekti yazma.

14. Parantez veya köşeli parantez kullanma.

15. "[Hüzünlü müzik]", "(kamera yaklaşır)",
"Sahne 1", "Bölüm 1" gibi ifadeler yazma.

16. İzleyici bölümlere ayrıldığını fark etmemeli.

17. Anlatım kesintisiz tek bir belgesel akışı
gibi hissettirmeli.

18. Sadece seçilen bilim insanı, mucit veya kaşifin
hikayesini anlat.

19. Gereksiz siyasi propaganda oluşturma.

20. Diktatör veya savaş suçlusu seçme.

21. Gerçek bir insanın hayatındaki mücadele,
haksızlık, başarısızlık, yalnızlık, keşif,
zafer veya trajediyi doğal şekilde anlat.

22. Abartılı ve doğrulanamayan iddialardan kaçın.

23. Metin doğrudan seslendirmeye uygun olmalı.

Sadece gerçek anlatım cümleleri yaz.
"""

# =========================================================
# GEMINI API
# =========================================================

def call_gemini(prompt, max_retries=3):

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY bulunamadı.")
        return None

    for attempt in range(
        1,
        max_retries + 1
    ):

        print(
            f"🤖 Gemini isteği "
            f"{attempt}/{max_retries}"
        )

        print(
            f"🧠 Gemini model: "
            f"{GEMINI_MODEL}"
        )

        try:

            response = requests.post(

                GEMINI_URL,

                params={
                    "key": GEMINI_API_KEY
                },

                headers={
                    "Content-Type":
                    "application/json"
                },

                json={

                    "contents": [

                        {
                            "parts": [

                                {
                                    "text":
                                    prompt
                                }

                            ]
                        }

                    ],

                    "generationConfig": {

                        "temperature": 0.7,

                        "maxOutputTokens":
                        12000

                    }

                },

                timeout=300

            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            # -------------------------------------------------
            # BAŞARILI
            # -------------------------------------------------

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

                        print(
                            response.text[:3000]
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
                            "❌ Gemini parts boş."
                        )

                        print(
                            response.text[:3000]
                        )

                        return None

                    text = parts[0].get(
                        "text",
                        ""
                    )

                    if text and text.strip():

                        print(
                            "✅ Gemini başarıyla "
                            "cevap verdi."
                        )

                        return text.strip()

                    print(
                        "❌ Gemini boş cevap verdi."
                    )

                    return None

                except Exception as e:

                    print(
                        "❌ Gemini JSON "
                        "okuma hatası:",
                        str(e)
                    )

                    print(
                        response.text[:5000]
                    )

                    return None

            # -------------------------------------------------
            # 429 KOTA
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429: "
                    "kota veya hız limiti."
                )

                if attempt >= max_retries:

                    print(
                        "❌ Gemini retry "
                        "limiti doldu."
                    )

                    return None

                wait_time = (
                    15 * attempt
                    + random.randint(0, 5)
                )

                print(
                    f"⏳ {wait_time} saniye "
                    "bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # -------------------------------------------------
            # GEÇİCİ SUNUCU HATASI
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                print(
                    "⚠️ Gemini geçici "
                    "sunucu hatası:",
                    response.status_code
                )

                if attempt >= max_retries:
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

            # -------------------------------------------------
            # MODEL / API HATASI
            # -------------------------------------------------

            if response.status_code == 404:

                print(
                    "❌ Gemini modeli "
                    "bulunamadı."
                )

                print(
                    "🧠 Kullanılan model:",
                    GEMINI_MODEL
                )

                print(
                    "📥 Gemini hata cevabı:"
                )

                print(
                    response.text[:5000]
                )

                return None

            # -------------------------------------------------
            # API KEY HATASI
            # -------------------------------------------------

            if response.status_code in {
                400,
                401,
                403
            }:

                print(
                    "❌ Gemini API "
                    "kimlik doğrulama/"
                    "yetki hatası."
                )

                print(
                    response.text[:5000]
                )

                return None

            # -------------------------------------------------
            # DİĞER HATALAR
            # -------------------------------------------------

            print(
                "❌ Gemini kalıcı hata:"
            )

            print(
                response.text[:5000]
            )

            return None

        # -----------------------------------------------------
        # TIMEOUT
        # -----------------------------------------------------

        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt >= max_retries:
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

        # -----------------------------------------------------
        # NETWORK
        # -----------------------------------------------------

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini ağ hatası:"
            )

            print(
                str(e)
            )

            if attempt >= max_retries:
                return None

            time.sleep(10)

        except Exception as e:

            print(
                "❌ Beklenmeyen Gemini "
                "hatası:",
                str(e)
            )

            return None

    return None


# =========================================================
# SADECE GEMINI
# =========================================================

def call_ai(prompt):

    print()
    print("================================")
    print("🤖 ANA SİSTEM: GEMINI")
    print("🧠 MODEL:", GEMINI_MODEL)
    print("🚫 CEREBRAS: DEVRE DIŞI")
    print("🚫 NVIDIA: DEVRE DIŞI")
    print("================================")

    result = call_gemini(
        prompt,
        max_retries=3
    )

    if result:

        print(
            "✅ İçerik Gemini tarafından "
            "üretildi."
        )

        return result

    raise SystemExit(
        "❌ Gemini içerik üretemedi."
    )


# =========================================================
# GEÇMİŞ
# =========================================================

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

        except Exception as e:

            print(
                "⚠️ Konu geçmişi "
                "okunamadı:",
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

    if not re.search(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}",
        topic
    ):
        return False

    if len(topic.split()) < 2:
        return False

    return True


# =========================================================
# KONU + BÖLÜM PLANI
# =========================================================

def generate_topic_and_outline(
    history
):

    if history:

        avoid_list = "\n".join(
            f"- {t}"
            for t in history
        )

    else:

        avoid_list = (
            "(henüz konu geçmişi yok)"
        )

    prompt = f"""

Sen "DAHİLER VE KEŞİFLER" adlı
Türkçe bilgi/tarih/bilim YouTube
kanalı için 30-45 dakikalık
belgeseller hazırlayan profesyonel
editör ve senaristsin.

KANAL NİŞİ:

Kanal yalnızca bilim insanlarının,
mucitlerin ve kaşiflerin insani ve
dramatik hikayelerine odaklanıyor.

Kuru bilgi anlatımı istemiyoruz.

Bir insanın yaşadığı:

haksızlık,
yalnızlık,
mücadele,
başarısızlık,
dışlanma,
geç fark edilme,
büyük keşif,
trajedi,
fedakarlık
veya başarı

hikayenin merkezinde olmalı.

ÖRNEK KONU TARZLARI:

{ORNEK_KONULAR}

Daha önce kullanılan konular:

{avoid_list}

Bu konuların hiçbirini tekrar seçme.

Şimdi yeni ve gerçek bir bilim insanı,
mucit veya kaşif seç.

Konu 30-45 dakikalık bir belgeseli
dolduracak kadar zengin olmalı.

Diktatör veya savaş suçlusu seçme.

Genel savaş tarihi seçme.

Genel teknoloji tarihi seçme.

Günlük eşya seçme.

Sadece belirli bir bilim insanı,
mucit veya kaşifin hayatını ve
hikayesini seç.

5 bölümlük plan oluştur.

Her bölüm yaklaşık
{BOLUM_BASINA_KELIME} kelimelik
anlatımı taşıyabilecek kadar
ayrıntılı olmalı.

Toplam hedef:

{TOPLAM_HEDEF} kelime.

GÜÇLÜ AÇILIŞ:

İlk bölüm merak uyandırmalı.

İzleyici "Bu insana ne oldu?"
sorusunun cevabını öğrenmek istemeli.

DUYGUSAL AKIŞ:

Hikaye boyunca kişinin insani
tarafını göster.

Son bölüm güçlü ve duygusal
bir kapanışa sahip olsun.

KURALLAR:

- Bilgi uydurma.
- Gerçek ve doğrulanabilir kişi seç.
- Tarihleri mümkün olduğunca doğru kullan.
- Aynı kişiyi tekrar seçme.
- Propaganda yapma.
- Kışkırtıcı içerik üretme.
- Markdown kullanma.
- Yıldız kullanma.
- Başlık işaretleri kullanma.
- Gereksiz açıklama yazma.

ÇIKTIYI TAM OLARAK ŞU FORMATTA VER:

KONU: <konu>

BÖLÜM 1: <başlık> - <özet>

BÖLÜM 2: <başlık> - <özet>

BÖLÜM 3: <başlık> - <özet>

BÖLÜM 4: <başlık> - <özet>

BÖLÜM 5: <başlık> - <özet>

Sadece bu formatı kullan.
"""

    raw = call_ai(prompt)

    if not raw:
        return "", []

    topic = ""
    bolumler = []

    for line in raw.splitlines():

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
            or
            upper.startswith("BOLUM")
        ):

            bolumler.append(
                clean_line
            )

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip()

    topic = (
        topic
        .strip('"')
        .strip("'")
    )

    # Gemini bazen 5 yerine daha az bölüm verirse
    # sistemi tamamen durdurmamak için fallback.
    if topic and not bolumler:

        bolumler = [

            f"BÖLÜM 1: "
            f"Hayatının başlangıcı - "
            f"Konunun başlangıcı.",

            f"BÖLÜM 2: "
            f"Mücadele - "
            f"Bilimsel ve kişisel mücadele.",

            f"BÖLÜM 3: "
            f"Keşif - "
            f"En önemli çalışmalar ve keşif.",

            f"BÖLÜM 4: "
            f"Sonuçlar - "
            f"Keşfin etkileri ve yaşananlar.",

            f"BÖLÜM 5: "
            f"Miras - "
            f"Hayatının sonu ve bıraktığı miras."

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

ÖNCEKİ BÖLÜMÜN SON KISMI:

{previous_tail}

Bu noktadan doğal biçimde devam et.

Önceki cümleleri tekrar etme.
"""

    metadata_talimati = ""

    if need_metadata:

        metadata_talimati = f"""

SON BÖLÜMDESİN.

Anlatım bittikten sonra aşağıdaki
ayırıcıyı yaz:

{METADATA_AYIRICI}

Sonrasında:

BAŞLIK:

Merak uyandırıcı ama yanıltıcı
olmayan YouTube başlığı.

AÇIKLAMA:

3-5 cümlelik YouTube açıklaması.

ETİKETLER:

15-25 Türkçe etiket,
virgülle ayrılmış.
"""

    prompt = f"""

Sen "DAHİLER VE KEŞİFLER" adlı
YouTube kanalı için profesyonel
Türkçe bilim ve tarih belgeseli
anlatıcısısın.

ANA KONU:

{topic}

BÖLÜM PLANI:

{outline_text}

ŞU ANDA YAZILAN:

{chapter_line}

Bu bölüm yaklaşık
{BOLUM_BASINA_KELIME} kelime olmalı.

Bölümün amacı:

{chapter_index}/{total_chapters}

{devamlilik}

ANLATIM TARZI:

Belgesel anlatımı doğal,
ciddi ve akıcı olsun.

Kişinin yalnızca yaptığı keşifleri
anlatma.

İnsan olarak ne yaşadığını da
hissettir.

Ancak duygusal etki oluşturmak
için gerçek olmayan olaylar
uydurma.

Tarihler ve olaylar mümkün
olduğunca doğru olmalı.

İzleyici bunun bir bölüm olduğunu
hissetmemeli.

Bir önceki bölümün kaldığı yerden
doğal şekilde devam et.

TEKRAR YAPMA.

{NARRATION_KURALLARI}

ÇIKTI:

Sadece seslendirme metni.

Bölüm başlığı yazma.

Bölüm numarası yazma.

Sahne yazma.

Kamera hareketi yazma.

Müzik yazma.

Ses efekti yazma.

Parantez kullanma.

{metadata_talimati}
"""

    raw = call_ai(prompt)

    if not raw:
        return ""

    return raw.strip()


# =========================================================
# METADATA AYIRMA
# =========================================================

def parse_chapter_with_metadata(
    raw_text
):

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
        + topic[:95]
        + "\n\n"
        "AÇIKLAMA:\n"
        + topic
        + " hakkında kapsamlı "
          "bir belgesel.\n\n"
        "ETİKETLER:\n"
        "tarih, bilim, belgesel, "
        "keşif, bilim insanları, "
        "dahiler, bilgi"
    )


# =========================================================
# ANA PROGRAM
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
        f"{TOPLAM_HEDEF} kelime"
    )

    print(
        "Ana AI: Gemini 3.6 Flash"
    )

    print(
        "Cerebras: DEVRE DIŞI"
    )

    print(
        "NVIDIA: DEVRE DIŞI"
    )

    print("================================")
    print()

    # -----------------------------------------------------
    # KLASÖR
    # -----------------------------------------------------

    os.makedirs(
        OUT,
        exist_ok=True
    )

    # -----------------------------------------------------
    # GEÇMİŞ
    # -----------------------------------------------------

    history = load_history()

    topic = None
    bolumler = None

    # -----------------------------------------------------
    # KONU
    # -----------------------------------------------------

    print(
        "🧭 Konu + bölüm planı "
        "oluşturuluyor..."
    )

    for attempt in range(1, 3):

        print(
            f"🔄 Konu denemesi "
            f"{attempt}/2"
        )

        try:

            candidate_topic, candidate_bolumler = (
                generate_topic_and_outline(
                    history
                )
            )

            if (
                candidate_topic
                and
                is_valid_topic(
                    candidate_topic
                )
                and
                candidate_topic not in history
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

            if attempt < 2:
                time.sleep(5)

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 2:
                time.sleep(5)

    # -----------------------------------------------------
    # KONU KONTROL
    # -----------------------------------------------------

    if not topic:

        raise SystemExit(
            "❌ Geçerli konu üretilemedi."
        )

    # -----------------------------------------------------
    # BÖLÜM KONTROL
    # -----------------------------------------------------

    if not bolumler:

        raise SystemExit(
            "❌ Bölüm planı üretilemedi."
        )

    # Gemini 5'ten fazla/az bölüm verirse
    # mevcut planı kullan.
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

    # -----------------------------------------------------
    # GEÇMİŞE EKLE
    # -----------------------------------------------------

    if topic not in history:

        history.append(
            topic
        )

        save_history(
            history
        )

    # -----------------------------------------------------
    # KONU DOSYASI
    # -----------------------------------------------------

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            topic
        )

    # -----------------------------------------------------
    # BÖLÜMLER
    # -----------------------------------------------------

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

        print(
            f"📝 Bölüm "
            f"{idx}/{total}"
        )

        raw = generate_chapter(

            topic,

            outline_text,

            chapter_line,

            idx,

            total,

            previous_tail,

            need_metadata=is_last

        )

        chapter_text, maybe_metadata = (
            parse_chapter_with_metadata(
                raw
            )
        )

        if not chapter_text:

            print(
                f"⚠️ Bölüm {idx} "
                "boş geldi."
            )

            continue

        script_parts.append(
            chapter_text
        )

        previous_tail = (
            chapter_text[-800:]
        )

        if is_last:

            metadata_raw = (
                maybe_metadata
            )

        print(
            f"✅ Bölüm {idx}: "
            f"{len(chapter_text.split())} "
            "kelime"
        )

    # -----------------------------------------------------
    # SCRIPT KONTROL
    # -----------------------------------------------------

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )

    full_script = (
        "\n\n".join(
            script_parts
        )
    )

    toplam_kelime = len(
        full_script.split()
    )

    print()
    print(
        "📊 Toplam kelime:",
        toplam_kelime
    )

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    if metadata_raw:

        metadata_text = (
            metadata_raw.strip()
        )

    else:

        print(
            "⚠️ Metadata üretilemedi."
        )

        print(
            "⚠️ Varsayılan metadata "
            "kullanılıyor."
        )

        metadata_text = (
            default_metadata(
                topic
            )
        )

    # -----------------------------------------------------
    # SON DOSYA
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # TAMAMLANDI
    # -----------------------------------------------------

    print()
    print("================================")
    print(
        "✅ İÇERİK OLUŞTURULDU"
    )
    print("================================")

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
        "🧠 AI: Gemini 3.6 Flash"
    )

    print(
        "🚫 Cerebras kullanılmadı."
    )

    print(
        "🚫 NVIDIA kullanılmadı."
    )

    print("================================")


# =========================================================
# BAŞLAT
# =========================================================

if __name__ == "__main__":
    main()
