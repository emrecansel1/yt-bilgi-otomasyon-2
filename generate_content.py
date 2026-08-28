import os
import json
import requests
import re
import time
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY bulunamadı.")

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(REPO_BASE, "video_topic_history.json")
OUTPUT_FILE = os.path.join(OUT, "current_content.txt")

URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

MAX_HISTORY = 30

# 1 saatlik seslendirmeyi (~9000 kelime) az sayıda büyük bölümde
# doldurup Gemini isteğini azaltıyoruz.
BOLUM_SAYISI = 3
BOLUM_BASINA_KELIME = 3000

METADATA_AYIRICI = "===METADATA_AYIRICI==="

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
Bu bir film senaryosu değildir. Sahne yazma. Kamera hareketi
yazma. Karakter hareketi yazma. Müzik veya ses efekti yazma.
Parantez kullanma. Köşeli parantez kullanma. "[Hüzünlü müzik]",
"(kamera yaklaşır)", "Sahne 1", "Bölüm 1" gibi ifadeler
kesinlikle yazma. İzleyici bölümlere ayrıldığını fark etmemeli,
anlatım kesintisiz tek bir belgesel akışı gibi hissetmeli.

Sadece seçilen konuyu doğrudan anlat. Metin doğrudan TTS
sistemine gönderileceği için okuyucu yalnızca gerçek anlatım
cümlelerini görmelidir.
"""


def call_gemini_with_retry(prompt, max_retries=5):
    retry_statuses = {429, 500, 502, 503, 504}

    for attempt in range(1, max_retries + 1):
        print(f"🤖 Gemini isteği {attempt}/{max_retries}")

        try:
            response = requests.post(
                URL,
                params={"key": API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=180
            )

            print("HTTP:", response.status_code)

            if response.ok:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

            if response.status_code in retry_statuses:
                if attempt >= max_retries:
                    print("❌ Gemini tekrar deneme hakkı bitti.")
                    print(response.text)
                    raise SystemExit(1)

                wait_time = 15 * (2 ** (attempt - 1)) + random.randint(0, 5)
                print(f"⚠️ Gemini geçici olarak {response.status_code} döndürdü.")
                print(f"⏳ {wait_time} saniye sonra tekrar denenecek...")
                time.sleep(wait_time)
                continue

            print("❌ Gemini kalıcı hata döndürdü.")
            print(response.text)
            raise SystemExit(1)

        except requests.exceptions.Timeout:
            if attempt >= max_retries:
                print("❌ Gemini zaman aşımı nedeniyle başarısız oldu.")
                raise SystemExit(1)
            wait_time = 15 * (2 ** (attempt - 1)) + random.randint(0, 5)
            print("⚠️ İstek zaman aşımına uğradı.")
            print(f"⏳ {wait_time} saniye sonra tekrar denenecek...")
            time.sleep(wait_time)

        except requests.exceptions.RequestException as e:
            if attempt >= max_retries:
                print("❌ Ağ hatası nedeniyle Gemini isteği başarısız oldu.")
                print(str(e))
                raise SystemExit(1)
            wait_time = 15 * (2 ** (attempt - 1)) + random.randint(0, 5)
            print("⚠️ Ağ hatası:", str(e))
            print(f"⏳ {wait_time} saniye sonra tekrar denenecek...")
            time.sleep(wait_time)

    raise SystemExit(1)


def load_history():
    if os.path.exists(TOPIC_HISTORY_FILE):
        try:
            with open(TOPIC_HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    history = history[-MAX_HISTORY:]
    with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_valid_topic(topic):
    if not topic:
        return False
    if len(topic) < 8 or len(topic) > 220:
        return False
    if not re.search(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", topic):
        return False
    if len(topic.split()) < 2:
        return False
    return True


def generate_topic_and_outline(history):
    avoid_list = "\n".join(f"- {t}" for t in history) if history else "(henüz yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe bilgi/tarih/bilim YouTube
kanalı için 1 SAATLİK belgesel formatında uzun video hazırlayan
bir editör VE senaristsin. Bu tek istekte HEM konuyu seçeceksin
HEM de o konunun bölüm planını (outline) çıkaracaksın.

1. ADIM - KONU SEÇ:
Seçtiğin konu, en az 45-60 dakikalık zengin, derinlemesine bir
belgesel anlatımını doldurabilecek kadar GENİŞ ve DERİN olmalı.
Tek bir küçük ilginç bilgi veya kısa bir olay YETERSİZDİR.

İyi örnekler (kapsam olarak):
- Bir tarihi kişinin tüm hayatı ve mirası (diktatör/savaş
  suçlusu olmayan).
- Bir antik uygarlığın yükselişi ve çöküşü.
- Büyük bir tarihi olayın veya dönemin bütün boyutlarıyla
  anlatımı.
- Bir bilim dalının veya büyük keşfin baştan sona hikâyesi.
- Çözülmemiş büyük bir gizemin tüm açılardan incelenmesi.

KESİNLİKLE ŞU DAHA ÖNCE KULLANILAN KONULARI TEKRAR SEÇME
(bunlara çok benzer/aynı konuları da seçme):
{avoid_list}

2. ADIM - BÖLÜM PLANI ÇIKAR:
Bu konuyu {BOLUM_SAYISI} büyük bölümde anlatacak bir belgesel
bölüm planı hazırla. Her bölüm yaklaşık {BOLUM_BASINA_KELIME}
kelimelik anlatıma denk gelecek şekilde tasarlanmalı, toplamda
~1 saatlik bir belgesel oluşturmalı.

KURALLAR:
- 1. bölüm çok güçlü bir açılış/merak unsuru içermeli.
- Ortadaki bölümler konuyu derinlemesine, kronolojik veya
  mantıklı bir sırayla işlemeli.
- Son bölüm konunun insanlık/tarih/bilim açısından önemiyle
  kapanmalı.
- Bölümler birbirinin devamı olmalı, konu tekrarı olmamalı.
- Siyasi propaganda, savaş suçluları, diktatörler, hakaret veya
  kışkırtıcı içerik ÖNERME.
- Sadece gerçek, doğrulanabilir bir konu olsun.

ÇIKTI FORMATI (tam olarak bunu kullan, başka hiçbir açıklama
ekleme):

KONU: <seçtiğin konu, tek satır>
BÖLÜM 1: <kısa başlık> - <bu bölümde anlatılacakların 1-2 cümlelik özeti>
BÖLÜM 2: <kısa başlık> - <özet>
BÖLÜM 3: <kısa başlık> - <özet>
"""

    raw = call_gemini_with_retry(prompt)

    topic = ""
    bolumler = []

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("KONU:"):
            topic = line.split(":", 1)[1].strip()
        elif line.upper().startswith("BÖLÜM") or line.upper().startswith("BOLUM"):
            bolumler.append(line)

    topic = re.sub(r"\s+", " ", topic).strip().strip('"').strip()

    if not bolumler:
        bolumler = [f"BÖLÜM 1: {topic} - Konunun genel anlatımı"]

    return topic, bolumler


def generate_chapter(topic, outline_text, chapter_line, chapter_index, total_chapters, previous_tail, need_metadata):
    devamlilik = ""

    if previous_tail:
        devamlilik = f"""
BİR ÖNCEKİ BÖLÜMÜN SON KISMI (buradan doğal şekilde devam et,
tekrar etme, aynı cümleleri kurma, ama konudan da kopma):
\"\"\"{previous_tail}\"\"\"
"""

    metadata_talimati = ""
    if need_metadata:
        metadata_talimati = f"""

BU SON BÖLÜM OLDUĞU İÇİN, bölüm metnini yazdıktan SONRA, tam
olarak şu satırı yaz:
{METADATA_AYIRICI}

Ardından bu 1 saatlik belgesel video için YouTube metadata'sı
ekle, tam olarak şu formatta:

BAŞLIK:
YouTube için merak uyandırıcı ama yanıltıcı olmayan başlık.

AÇIKLAMA:
Videonun 3-5 cümlelik açıklaması.

ETİKETLER:
Konuya uygun 15-25 Türkçe YouTube etiketi, virgülle ayrılmış.
"""

    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için çalışan
profesyonel tarih/bilim belgeseli anlatıcısısın.

GENEL KONU:
{topic}

TÜM BÖLÜM PLANI (bağlam için, sadece sen bunu bilirsin,
izleyiciye bölüm numarası veya başlığı SÖYLEME):
{outline_text}

ŞİMDİ YAZACAĞIN BÖLÜM ({chapter_index}/{total_chapters}):
{chapter_line}
{devamlilik}
GÖREV:
Bu bölüm için yaklaşık {BOLUM_BASINA_KELIME} kelimelik, akıcı,
kesintisiz belgesel anlatım metni yaz. Bu metin, izleyicinin
"bölüm" olduğunu fark etmeyeceği şekilde, bir öncekiyle
kaynaşmış tek bir anlatının parçası gibi olmalı.

{NARRATION_KURALLARI}

ÇIKTI SADECE BU BÖLÜMÜN SESLENDİRME METNİ OLMALI. Başlık, numara
veya başka hiçbir şey yazma.
{metadata_talimati}
"""

    raw = call_gemini_with_retry(prompt)
    return raw.strip()


def parse_chapter_with_metadata(raw_text):
    if METADATA_AYIRICI in raw_text:
        narration, metadata = raw_text.split(METADATA_AYIRICI, 1)
        return narration.strip(), metadata.strip()
    return raw_text.strip(), None


def default_metadata(topic):
    return (
        f"BAŞLIK:\n{topic[:95]}\n\n"
        f"AÇIKLAMA:\n{topic} hakkında kapsamlı bir belgesel.\n\n"
        f"ETİKETLER:\ntarih, bilim, belgesel, keşif, bilgi"
    )


def main():
    print("================================")
    print("🎬 BÖLÜMLÜ BELGESEL SENARYO MOTORU (AZALTILMIŞ İSTEK)")
    print("================================")
    print(f"Hedef: {BOLUM_SAYISI} bölüm x ~{BOLUM_BASINA_KELIME} kelime "
          f"(~{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime toplam)")
    print()

    history = load_history()
    topic = None
    bolumler = None

    print("🧭 1/2 Konu + bölüm planı (TEK istekte) oluşturuluyor...")

    for attempt in range(4):
        try:
            candidate_topic, candidate_bolumler = generate_topic_and_outline(history)

            if candidate_topic and is_valid_topic(candidate_topic) and candidate_topic not in history:
                topic = candidate_topic
                bolumler = candidate_bolumler
                break

            print(f"   ⚠️ Geçersiz/tekrar konu geldi ({candidate_topic!r}), yeniden deneniyor...")

        except Exception as e:
            print("   ⚠️ Konu+plan üretim hatası:", e)
            time.sleep(5)

    if not topic:
        raise SystemExit("❌ Yapay zeka geçerli bir konu+plan üretemedi.")

    outline_text = "\n".join(bolumler)

    print("🎯 Seçilen konu:", topic)
    print("Bölüm planı:")
    for b in bolumler:
        print("  -", b)
    print()

    history.append(topic)
    save_history(history)

    os.makedirs(OUT, exist_ok=True)
    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        f.write(topic)

    print("✍️ 2/2 Bölümler tek tek yazılıyor (son bölümde metadata da üretilecek)...")

    script_parts = []
    previous_tail = None
    metadata_raw = None

    total = len(bolumler)

    for idx, chapter_line in enumerate(bolumler, 1):
        is_last = (idx == total)

        print(f"   📝 Bölüm {idx}/{total} yazılıyor: {chapter_line[:70]}")

        raw = generate_chapter(
            topic, outline_text, chapter_line, idx, total, previous_tail,
            need_metadata=is_last
        )

        chapter_text, maybe_metadata = parse_chapter_with_metadata(raw)

        if not chapter_text:
            print(f"   ⚠️ Bölüm {idx} boş geldi, atlanıyor.")
            continue

        script_parts.append(chapter_text)
        previous_tail = chapter_text[-500:]

        if is_last:
            metadata_raw = maybe_metadata

        kelime = len(chapter_text.split())
        print(f"   ✅ Bölüm {idx} tamam - {kelime} kelime")

    if not script_parts:
        raise SystemExit("❌ Hiçbir bölüm üretilemedi.")

    full_script = "\n\n".join(script_parts)

    toplam_kelime = len(full_script.split())
    print()
    print(f"📊 Toplam senaryo: {toplam_kelime} kelime (~{round(toplam_kelime/150)} dakika tahmini)")

    if not metadata_raw:
        print("⚠️ Metadata son bölümle birlikte gelmedi, varsayılan metadata kullanılıyor "
              "(ekstra Gemini isteği yapılmıyor).")
        metadata_raw = default_metadata(topic)

    final_text = (
        "=== SESLENDİRME METNİ ===\n"
        + full_script
        + "\n\n=== METADATA ===\n"
        + metadata_raw
    )

    if not final_text.strip():
        print("❌ İçerik boş oluştu.")
        raise SystemExit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_text)

    print()
    print("================================")
    print(f"✅ İÇERİK OLUŞTURULDU (bu videoda {1 + total} Gemini isteği kullanıldı)")
    print("================================")
    print("Konu:", topic)
    print("Dosya:", OUTPUT_FILE)
    print("Toplam kelime:", toplam_kelime)
    print("Karakter:", len(final_text))
    print("================================")


if __name__ == "__main__":
    main()
