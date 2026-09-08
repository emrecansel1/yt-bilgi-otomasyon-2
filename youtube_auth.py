from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    SCOPES
)

creds = flow.run_local_server(port=0)

with open("token.json", "w", encoding="utf-8") as f:
    f.write(creds.to_json())

print()
print("=" * 50)
print("✅ YENİ YOUTUBE TOKEN OLUŞTURULDU")
print("=" * 50)
print("📁 token.json hazır.")
print("📌 Şimdi token.json içeriğini GitHub Secret'a koy.")
print("=" * 50)
