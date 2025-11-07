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

# 🔹 Hem Sheets hem Drive yetkileri
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# Drive klasör ID'nizi buraya yazın
FOLDER_ID = "1xmFTBMmKCjm2cKEAA1NipufHjFnWXsLd"

def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_SHEETS_CREDENTIALS_JSON environment variable eksik!")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return creds

def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise Exception("SPREADSHEET_ID environment variable eksik!")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

def upload_to_drive(file):
    creds = get_creds()
    drive_service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": f"vardiya_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}",
        "parents": [FOLDER_ID]
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

@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        tarih = request.form.get("tarih")
        vardiya = request.form.get("vardiya")
        hat = request.form.get("hat")
        aciklamalar = json.loads(request.form.get("aciklamalar", "[]"))

        # Temel alanlar dolu olmasa da kaydetmeye izin veriyoruz
        ws = get_sheet()

        for i, item in enumerate(aciklamalar):
            aciklama = item.get("aciklama", "")
            personel = item.get("personel", "")
            file = request.files.get(f"foto{i}")
            link = ""
            if file:
                print(f"📤 Dosya bulundu: {file.filename}")
                link = upload_to_drive(file)
                print(f"🌐 Drive link: {link}")

            ws.append_row([tarih, vardiya, hat, aciklama, personel, link])

        return jsonify({"mesaj": "Veriler Google Sheets ve Drive'a kaydedildi!"})

    except Exception as e:
        print("HATA:", e)
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
