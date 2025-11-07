import os
import sys
import io
import json
import gspread
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Render loglarının görünmesi için flush
print = lambda *args, **kwargs: __builtins__.print(*args, **kwargs, flush=True)

app = Flask(__name__)
CORS(app)

# 🔹 Google Sheets ve Drive bağlantısı
def get_creds():
    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        raise Exception("PRIVATE_KEY environment variable eksik!")
    creds_data = {
        "type": "service_account",
        "project_id": os.environ.get("PROJECT_ID"),
        "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
        "private_key": private_key.replace('\\n', '\n'),
        "client_email": os.environ.get("CLIENT_EMAIL"),
        "client_id": os.environ.get("CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("CLIENT_X509_CERT_URL"),
    }
    return Credentials.from_service_account_info(creds_data, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"
    ])

# 🔹 Google Sheets test fonksiyonu
def test_sheets():
    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).worksheet("Sayfa1")
        sheet.append_row(["TEST", "BAĞLANTI", "OK"], value_input_option="USER_ENTERED")
        print("✅ Google Sheets test satırı eklendi.")
    except Exception as e:
        print("🔥 Sheets test hatası:", e)

# 🔹 Fotoğrafı Drive’a yükleme
def upload_to_drive(file):
    creds = get_creds()
    drive_service = build("drive", "v3", credentials=creds)
    file_metadata = {
        "name": f"vardiya_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}",
        "parents": []
    }
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.mimetype)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    file_id = uploaded_file.get("id")
    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()
    return f"https://drive.google.com/file/d/{file_id}/view"

# 🔹 Form verilerini kaydet
@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        tarih = request.form.get("tarih") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        vardiya = request.form.get("vardiya", "")
        hat = request.form.get("hat", "")
        aciklamalar = json.loads(request.form.get("aciklamalar", "[]"))

        creds = get_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).worksheet("Sayfa1")

        for i, item in enumerate(aciklamalar):
            aciklama = item.get("aciklama", "")
            personel = item.get("personel", "")
            file = request.files.get(f"foto{i}")
            link = ""
            if file:
                link = upload_to_drive(file)

            row = [tarih, vardiya, hat, aciklama, personel, link]
            sheet.append_row(row, value_input_option="USER_ENTERED")
            print("✅ Satır eklendi:", row)

        return jsonify({"mesaj": "Veriler Google Sheets ve Drive'a kaydedildi!"})

    except Exception as e:
        print("🔥 HATA:", e)
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    test_sheets()
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Flask sunucu başlatılıyor (port {port})...")
    app.run(host="0.0.0.0", port=port, debug=True)
