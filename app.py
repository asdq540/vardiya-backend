from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import json
import os
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Frontend'den gelen isteklere izin ver

# Google API yetki alanları
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Google kimlik bilgilerini al
def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_SHEETS_CREDENTIALS_JSON bulunamadı.")
    creds_dict = json.loads(creds_json)
    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

# Google Sheets bağlantısı
def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

# Google Drive'a fotoğraf yükle
def upload_to_drive(base64_data, file_name):
    try:
        if not base64_data.startswith("data:image"):
            return None  # resim değilse geç
        creds = get_creds()
        drive_service = build("drive", "v3", credentials=creds)

        folder_id = os.environ.get("DRIVE_FOLDER_ID")
        if not folder_id:
            raise Exception("DRIVE_FOLDER_ID ortam değişkeni bulunamadı.")

        # Base64'ü decode et
        file_bytes = base64.b64decode(base64_data.split(",")[1])
        file_stream = io.BytesIO(file_bytes)

        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }

        media = MediaIoBaseUpload(file_stream, mimetype="image/jpeg")
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = file.get("id")

        # Paylaşımı "herkese açık" yap
        drive_service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"}
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"

    except Exception as e:
        print("Fotoğraf yüklenemedi:", e)
        return None

# API route: Sheets'e verileri kaydet
@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        data = request.get_json()
        tarih = data.get("tarih")
        vardiya = data.get("vardiya")
        hat = data.get("hat")
        aciklamalar = data.get("aciklamalar", [])

        ws = get_sheet()
        rows_to_add = []

        for i, item in enumerate(aciklamalar):
            aciklama = item.get("aciklama", "").strip()
            personel = item.get("personel", "").strip()
            foto_data = item.get("foto", "")

            foto_url = ""
            if foto_data:
                file_name = f"{tarih}_{vardiya}_{hat}_{i+1}.jpg"
                foto_url = upload_to_drive(foto_data, file_name) or "Fotoğraf yüklenemedi"

            if aciklama or personel or foto_url:
                rows_to_add.append([tarih, vardiya, hat, aciklama, personel, foto_url])

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="RAW")

        return jsonify({"mesaj": "Veriler başarıyla eklendi!"}), 200

    except Exception as e:
        print("Sheets veya Drive hatası:", e)
        return jsonify({"hata": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
