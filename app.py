from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import base64
import requests
import traceback
import time  # <-- benzersiz isim için ekledik

app = Flask(__name__)
CORS(app)

# Google API yetki alanları
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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
    if not spreadsheet_id:
        raise Exception("SPREADSHEET_ID bulunamadı.")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

def upload_to_imgbb(base64_data, file_name):
    try:
        api_key = os.environ.get("IMGBB_API_KEY")
        if not api_key:
            raise Exception("IMGBB_API_KEY bulunamadı.")

        if not base64_data.startswith("data:image"):
            print("⚠️ Geçersiz resim formatı atlandı.")
            return None

        image_bytes = base64_data.split(",")[1]

        payload = {
            "key": api_key,
            "image": image_bytes,
            "name": file_name
        }

        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        print("Status code:", response.status_code)
        print("Response text:", response.text)

        data = response.json()
        if data.get("success"):
            return data["data"]["url"]
        else:
            print("🚨 ImgBB Error:", data.get("error", {}).get("message"))
            return None

    except Exception:
        print("🚨 Fotoğraf yüklenemedi:")
        traceback.print_exc()
        return None

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
                timestamp = int(time.time() * 1000)  # milisaniye damgası
                file_name = f"{tarih}_{vardiya}_{hat}_{i+1}_{timestamp}"
                foto_url = upload_to_imgbb(foto_data, file_name) or "Fotoğraf yüklenemedi"

            if aciklama or personel or foto_url:
                rows_to_add.append([tarih, vardiya, hat, aciklama, personel, foto_url])

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="RAW")

        return jsonify({"mesaj": "Veriler başarıyla eklendi!"}), 200

    except Exception as e:
        print("❌ Genel hata:")
        traceback.print_exc()
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
