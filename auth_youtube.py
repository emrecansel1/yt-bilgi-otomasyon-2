from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secrets.json",
    SCOPES
)

creds = flow.run_local_server(
    host="127.0.0.1",
    port=0,
    open_browser=False,
    access_type="offline",
    prompt="consent"
)

with open("token.json", "w") as f:
    f.write(creds.to_json())

youtube = build("youtube", "v3", credentials=creds)

response = youtube.channels().list(
    part="snippet",
    mine=True
).execute()

for channel in response.get("items", []):
    print("KANAL:", channel["snippet"]["title"])

print("OAuth BASARILI")
