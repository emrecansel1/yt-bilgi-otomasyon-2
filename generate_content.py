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
    raise RuntimeError(
        'Kullanım: python generate_content.py "KONU"'
    )

KONU = " ".join(sys.argv[1:]).strip()

URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

PROMPT = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için çalışan
profesyonel tarih, bilim ve bilgi belgeseli içerik üreticisisin.

KONU:
{KONU}

Bu konu hakkında Türkçe, en az 15 dakikalık,
seslendirmeye uygun kaliteli bir YouTube uzun video içeriği hazırla.

AMAÇ:
İzleyicinin ilk saniyeden itibaren merak etmesini ve videonun
sonuna kadar izlemek istemesini sağlamak.

KURALLAR:

1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Doğrulanamayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. İlk 20 saniye çok güçlü bir merak unsuru içersin.
6. Gereksiz tekrar yapma.
7. Konuyu mantıklı bir akışla anlat.
8. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
9. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
10. Son bölümde konunun insanlık açısından önemini anlat.
11. Metin seslendirmeye uygun olsun.
12. En az 15 dakikalık seslendirmeye yetecek uzunlukta olsun.

Ayrıca videonun sonunda ayrı bir METADATA bölümü oluştur.

Şu formatı kullan:

=== SESLENDİRME METNİ ===
Buraya yalnızca anlatıcının okuyacağı bilgi metnini yaz.

ÖNEMLİ:
Bu bir film senaryosu değildir.
Sahne yazma.
Kamera hareketi yazma.
Karakter hareketi yazma.
Müzik veya ses efekti yazma.
Parantez kullanma.
Köşeli parantez kullanma.
"[Hüzünlü müzik]", "(kamera yaklaşır)", "Sahne 1" gibi ifadeler kesinlikle yazma.

Sadece seçilen konuyu doğrudan anlat.
Metin doğrudan TTS sistemine gönderileceği için okuyucu yalnızca gerçek anlatım cümlelerini görmelidir.

Örnek:
"Albert Einstein, modern fiziğin en önemli bilim insanlarından biriydi. 1879 yılında Almanya'da doğdu..."

Yanlış:
"[Hüzünlü müzik başlar.] Einstein odasında oturuyordu. Kamera yavaşça ona yaklaşır..."

ÇIKTI SADECE SESLENDİRME METNİ OLMALI.

=== METADATA ===
BAŞLIK:
YouTube için merak uyandırıcı ama yanıltıcı olmayan başlık.

AÇIKLAMA:
Videonun açıklaması.

ETİKETLER:
Konuya uygun 15-25 Türkçe YouTube etiketi.
Etiketleri virgülle ayır.

Çıktıyı Türkçe üret.
"""


def generate_content():
    max_attempts = 5

    retry_statuses = {
        429, 500, 502, 503, 504
    }

    for attempt in range(1, max_attempts + 1):

        print()
        print(
            f"🤖 Gemini isteği "
            f"{attempt}/{max_attempts}"
        )

        try:
            response = requests.post(
                URL,
                params={"key": API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": PROMPT}
                            ]
                        }
                    ]
                },
                timeout=180
            )

            print("HTTP:", response.status_code)

            if response.ok:
                return response

            if response.status_code in retry_statuses:

                if attempt >= max_attempts:
                    print(
                        "❌ Gemini tekrar deneme hakkı bitti."
                    )
                    print(response.text)
                    raise SystemExit(1)

                wait_time = (
                    15 * (2 ** (attempt - 1))
                    + random.randint(0, 5)
                )

                print(
                    f"⚠️ Gemini geçici olarak "
                    f"{response.status_code} döndürdü."
                )

                print(
                    f"⏳ {wait_time} saniye sonra "
                    f"tekrar denenecek..."
                )

                time.sleep(wait_time)
                continue

            print("❌ Gemini kalıcı hata döndürdü.")
            print(response.text)
            raise SystemExit(1)

        except requests.exceptions.Timeout:

            if attempt >= max_attempts:
                print(
                    "❌ Gemini zaman aşımı nedeniyle "
                    "başarısız oldu."
                )
                raise SystemExit(1)

            wait_time = (
                15 * (2 ** (attempt - 1))
                + random.randint(0, 5)
            )

            print(
                f"⚠️ İstek zaman aşımına uğradı."
            )

            print(
                f"⏳ {wait_time} saniye sonra "
                f"tekrar denenecek..."
            )

            time.sleep(wait_time)

        except requests.exceptions.RequestException as e:

            if attempt >= max_attempts:
                print(
                    "❌ Ağ hatası nedeniyle "
                    "Gemini isteği başarısız oldu."
                )
                print(str(e))
                raise SystemExit(1)

            wait_time = (
                15 * (2 ** (attempt - 1))
                + random.randint(0, 5)
            )

            print("⚠️ Ağ hatası:", str(e))

            print(
                f"⏳ {wait_time} saniye sonra "
                f"tekrar denenecek..."
            )

            time.sleep(wait_time)

    raise SystemExit(1)


response = generate_content()

try:
    data = response.json()

    text = (
        data["candidates"][0]
        ["content"]["parts"][0]["text"]
    )

except Exception as e:
    print("❌ Gemini yanıtı okunamadı.")
    print(str(e))
    print(response.text)
    raise SystemExit(1)


if not text.strip():
    print("❌ Gemini boş içerik döndürdü.")
    raise SystemExit(1)


os.makedirs(OUT, exist_ok=True)

output_file = os.path.join(
    OUT,
    "current_content.txt"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:
    f.write(text)


print()
print("================================")
print("✅ İÇERİK OLUŞTURULDU")
print("================================")
print("Konu:", KONU)
print("Dosya:", output_file)
print("Karakter:", len(text))
print("================================")
