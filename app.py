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

# 📜 Google API erişim kapsamları
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 🔐 Kimlik bilgilerini yükle
def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_SHEETS_CREDENTIALS_JSON bulunamadı.")
    creds_dict = json.loads(creds_json)
    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

# 📗 Google Sheet erişimi
def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

# 🖼️ Google Drive’a fotoğraf yükleme
def upload_to_drive(base64_data, filename):
    try:
        creds = get_creds()
        service = build("drive", "v3", credentials=creds)

        folder_id = "1xmFTBMmKCjm2cKEAA1NipufHjFnWXsLd"  # 📁 senin klasör ID'in
        mime_type = "image/jpeg"

        file_data = base64.b64decode(base64_data.split(",")[1])
        file_stream = io.BytesIO(file_data)

        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }

        media = MediaIoBaseUpload(file_stream, mimetype=mime_type)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        # 📢 Herkese görünür hale getir
        service.permissions().create(
            fileId=uploaded_file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        # 📎 Paylaşılabilir link oluştur
        file_url = f"https://drive.google.com/uc?id={uploaded_file['id']}"
        print(f"✅ Fotoğraf yüklendi: {file_url}")
        return file_url

    except Exception as e:
        print("❌ Drive yükleme hatası:", e)
        return "Yüklenemedi"

# 🧾 Ana kayıt fonksiyonu
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

        for item in aciklamalar:
            aciklama = item.get("aciklama", "").strip()
            personel = item.get("personel", "").strip()
            foto_data = item.get("foto", "")
            foto_url = ""

            # 📸 Fotoğraf varsa Drive’a yükle
            if foto_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{tarih}_{vardiya}_{hat}_{timestamp}.jpg"
                foto_url = upload_to_drive(foto_data, filename)

            # Boş olmayan satırları ekle
            if aciklama or personel or foto_url:
                rows_to_add.append([tarih, vardiya, hat, aciklama, personel, foto_url])

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="RAW")

        return jsonify({"mesaj": "✅ Veriler başarıyla kaydedildi!"}), 200

    except Exception as e:
        print("❌ Genel hata:", e)
        return jsonify({"hata": str(e)}), 500

# 🚀 Sunucuyu başlat
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
