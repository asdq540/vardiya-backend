from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 🔹 Google Sheets ve Drive yetkileri
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# 🔹 Kimlik bilgilerini ortam değişkeninden al
def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("Google Sheets kimlik bilgisi eksik.")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return creds

# 🔹 Google Sheet'e bağlan
def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

# 🔹 Dosyayı Google Drive'a yükle
def upload_to_drive(file):
    creds = get_creds()
    drive_service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": f"vardiya_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    }

    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.mimetype)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = uploaded_file.get("id")

    # Dosyayı herkese görünür yap
    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

# 🔹 Ana kayıt API'si
@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        tarih = request.form.get("tarih", "")
        vardiya = request.form.get("vardiya", "")
        hat = request.form.get("hat", "")
        aciklamalar_raw = request.form.get("aciklamalar", "[]")

        try:
            aciklamalar = json.loads(aciklamalar_raw)
        except json.JSONDecodeError:
            aciklamalar = []

        ws = get_sheet()
        kayit_sayisi = 0

        # 🔸 Her açıklama satırı için kayıt yap
        for i, item in enumerate(aciklamalar):
            aciklama = item.get("aciklama", "").strip()
            personel = item.get("personel", "").strip()
            file = request.files.get(f"foto{i}")
            link = ""

            if file and file.filename:
                link = upload_to_drive(file)

            ws.append_row([tarih, vardiya, hat, aciklama, personel, link])
            kayit_sayisi += 1

        # 🔸 Eğer hiç açıklama yoksa boş bir satır ekle (isteğe bağlı)
        if kayit_sayisi == 0:
            ws.append_row([tarih, vardiya, hat, "", "", ""])

        return jsonify({"mesaj": "Veriler Google Sheets ve Drive'a kaydedildi!"})

    except Exception as e:
        print("HATA:", e)
        return jsonify({"hata": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
