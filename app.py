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
CORS(app)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

FOLDER_ID = "1xmFTBMmKCjm2cKEAA1NipufHjFnWXsLd"  # senin klasör ID

def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_SHEETS_CREDENTIALS_JSON bulunamadı.")
    creds_dict = json.loads(creds_json)
    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

def upload_to_drive(base64_data, file_name):
    try:
        creds = get_creds()
        drive_service = build("drive", "v3", credentials=creds)

        # base64 prefix'ini temizle
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        file_bytes = base64.b64decode(base64_data)
        file_stream = io.BytesIO(file_bytes)
        media = MediaIoBaseUpload(file_stream, mimetype="image/jpeg")

        file_metadata = {"name": file_name, "parents": [FOLDER_ID]}

        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = uploaded.get("id")

        # herkese açık izni ver
        drive_service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        file_url = f"https://drive.google.com/uc?id={file_id}"
        print(f"✅ Fotoğraf yüklendi: {file_url}")
        return file_url

    except Exception as e:
        print("🚨 Google Drive yükleme hatası:", e)
        return ""

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

        for idx, item in enumerate(aciklamalar, start=1):
            aciklama = item.get("aciklama", "").strip()
            personel = item.get("personel", "").strip()
            foto = item.get("foto", "").strip()

            if not (aciklama or personel or foto):
                continue

            foto_url = ""
            if foto:
                file_name = f"{tarih}_{vardiya}_{hat}_foto_{idx}.jpg"
                foto_url = upload_to_drive(foto, file_name)

            rows_to_add.append([tarih, vardiya, hat, aciklama, personel, foto_url])

        if not rows_to_add:
            return jsonify({"mesaj": "Eklenebilecek veri bulunamadı."}), 400

        ws.append_rows(rows_to_add, value_input_option="RAW")
        return jsonify({
            "mesaj": f"{len(rows_to_add)} satır eklendi!",
            "veri": rows_to_add
        }), 200

    except Exception as e:
        print("🚨 Genel hata:", e)
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
