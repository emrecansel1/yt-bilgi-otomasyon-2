import os
import json
import requests
import sys
import time
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY bulunamadı.")

if len(sys.argv) < 2:
    raise RuntimeError('Kullanım: python generate_content.py "KONU"')

KONU = " ".join(sys.argv[1:]).strip()

URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

# 1 saatlik seslendirmeyi doldurmak için hedef toplam kelime sayısı
# ve bunu kaç bölüme yayacağımız.
BOLUM_SAYISI = 6
BOLUM_BASINA_KELIME = 1500

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
Bu bir film senaryosu değildir. Sahne yazma. Kamera hareketi yazma.
Karakter hareketi yazma. Müzik veya ses efekti yazma. Parantez
kullanma. Köşeli parantez kullanma. "[Hüzünlü müzik]",
"(kamera yaklaşır)", "Sahne 1", "Bölüm 1" gibi ifadeler kesinlikle
yazma. İzleyici bölümlere ayrıldığını fark etmemeli, anlatım kesintisiz
tek bir belgesel akışı gibi hissetmeli.

Sadece seçilen konuyu doğrudan anlat. Metin doğrudan TTS sistemine
gönderileceği için okuyucu yalnızca gerçek anlatım cümlelerini görmelidir.
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


def generate_outline(topic):
    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için çalışan profesyonel
belgesel senaristisin.

KONU:
{topic}

GÖREV:
Bu konuyu {BOLUM_SAYISI} bölümde anlatacak bir belgesel bölüm planı
(outline) hazırla. Her bölüm yaklaşık {BOLUM_BASINA_KELIME} kelimelik
anlatıma denk gelecek şekilde tasarlanmalı, toplamda ~1 saatlik bir
belgesel oluşturmalı.

KURALLAR:
- 1. bölüm çok güçlü bir açılış/merak unsuru içermeli.
- Ortadaki bölümler konuyu derinlemesine, kronolojik veya mantıklı
  bir sırayla işlemeli.
- Son bölüm konunun insanlık/tarih/bilim açısından önemiyle
  kapanmalı.
- Bölümler birbirinin devamı olmalı, konu tekrarı olmamalı.

ÇIKTI FORMATI (tam olarak bunu kullan):
BÖLÜM 1: <kısa başlık> - <bu bölümde anlatılacakların 1-2 cümlelik özeti>
BÖLÜM 2: <kısa başlık> - <özet>
...
BÖLÜM {BOLUM_SAYISI}: <kısa başlık> - <özet>

Başka hiçbir açıklama ekleme, sadece bu listeyi yaz.
"""

    raw = call_gemini_with_retry(prompt)

    bolumler = []

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith("BÖLÜM") or line.upper().startswith("BOLUM"):
            bolumler.append(line)

    if not bolumler:
        # Parse başarısız olursa tek bölüm gibi devam et, en azından çökmesin.
        bolumler = [f"BÖLÜM 1: {topic} - Konunun genel anlatımı"]

    return bolumler


def generate_chapter(topic, outline_text, chapter_line, chapter_index, total_chapters, previous_tail):
    devamlilik = ""

    if previous_tail:
        devamlilik = f"""
BİR ÖNCEKİ BÖLÜMÜN SON KISMI (buradan doğal şekilde devam et, tekrar
etme, aynı cümleleri kurma, ama konudan da kopma):
\"\"\"{previous_tail}\"\"\"
"""

    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için çalışan profesyonel
tarih/bilim belgeseli anlatıcısısın.

GENEL KONU:
{topic}

TÜM BÖLÜM PLANI (bağlam için, sadece sen bunu bilirsin, izleyiciye
bölüm numarası veya başlığı SÖYLEME):
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
"""

    raw = call_gemini_with_retry(prompt)
    return raw.strip()


def generate_metadata(topic, ilk_bolum_ozeti):
    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için çalışıyorsun.

KONU:
{topic}

BİRİNCİ BÖLÜMÜN AÇILIŞI (fikir vermesi için):
\"\"\"{ilk_bolum_ozeti[:800]}\"\"\"

GÖREV:
Bu 1 saatlik belgesel video için YouTube metadata'sı hazırla.

ÇIKTI FORMATI (tam olarak bunu kullan):
BAŞLIK:
YouTube için merak uyandırıcı ama yanıltıcı olmayan başlık.

AÇIKLAMA:
Videonun 3-5 cümlelik açıklaması.

ETİKETLER:
Konuya uygun 15-25 Türkçe YouTube etiketi, virgülle ayrılmış.

Çıktıyı Türkçe üret, başka hiçbir açıklama ekleme.
"""

    return call_gemini_with_retry(prompt).strip()


def main():
    print("================================")
    print("🎬 BÖLÜMLÜ BELGESEL SENARYO MOTORU")
    print("================================")
    print("Konu:", KONU)
    print(f"Hedef: {BOLUM_SAYISI} bölüm x ~{BOLUM_BASINA_KELIME} kelime "
          f"(~{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime toplam)")
    print()

    print("🧭 1/3 Bölüm planı (outline) oluşturuluyor...")
    bolumler = generate_outline(KONU)
    outline_text = "\n".join(bolumler)

    print("Bölüm planı:")
    for b in bolumler:
        print("  -", b)
    print()

    print("✍️ 2/3 Bölümler tek tek yazılıyor...")

    script_parts = []
    previous_tail = None

    total = len(bolumler)

    for idx, chapter_line in enumerate(bolumler, 1):
        print(f"   📝 Bölüm {idx}/{total} yazılıyor: {chapter_line[:70]}")

        chapter_text = generate_chapter(
            KONU, outline_text, chapter_line, idx, total, previous_tail
        )

        if not chapter_text:
            print(f"   ⚠️ Bölüm {idx} boş geldi, atlanıyor.")
            continue

        script_parts.append(chapter_text)

        # Devamlılık için son ~500 karakteri sakla.
        previous_tail = chapter_text[-500:]

        kelime = len(chapter_text.split())
        print(f"   ✅ Bölüm {idx} tamam - {kelime} kelime")

    if not script_parts:
        raise SystemExit("❌ Hiçbir bölüm üretilemedi.")

    full_script = "\n\n".join(script_parts)

    toplam_kelime = len(full_script.split())
    print()
    print(f"📊 Toplam senaryo: {toplam_kelime} kelime (~{round(toplam_kelime/150)} dakika tahmini)")

    print()
    print("🏷️ 3/3 Metadata oluşturuluyor...")
    metadata_raw = generate_metadata(KONU, script_parts[0])

    final_text = (
        "=== SESLENDİRME METNİ ===\n"
        + full_script
        + "\n\n=== METADATA ===\n"
        + metadata_raw
    )

    if not final_text.strip():
        print("❌ İçerik boş oluştu.")
        raise SystemExit(1)

    os.makedirs(OUT, exist_ok=True)

    output_file = os.path.join(OUT, "current_content.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)

    print()
    print("================================")
    print("✅ İÇERİK OLUŞTURULDU")
    print("================================")
    print("Konu:", KONU)
    print("Dosya:", output_file)
    print("Toplam kelime:", toplam_kelime)
    print("Karakter:", len(final_text))
    print("================================")


if __name__ == "__main__":
    main()
