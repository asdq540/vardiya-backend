import os
import sys
import base64
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# ✅ Logların Render’da görünmesi için
print = lambda *args, **kwargs: __builtins__.print(*args, **kwargs, flush=True)

app = Flask(__name__)
CORS(app)

# ✅ Google Sheets bağlantısı
def get_creds():
    creds_data = {
        "type": "service_account",
        "project_id": os.environ.get("PROJECT_ID"),
        "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
        "private_key": os.environ.get("PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("CLIENT_EMAIL"),
        "client_id": os.environ.get("CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("CLIENT_X509_CERT_URL"),
    }
    return Credentials.from_service_account_info(creds_data, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])

@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        data = request.get_json()
        print("📩 Alınan veri:", data)

        # Boş alan kontrolü KALDIRILDI
        ad_soyad = data.get("adSoyad", "")
        email = data.get("email", "")
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Google Sheets'e bağlan
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).worksheet("Sayfa1")

        # Açıklama alanları
        aciklamalar = [data.get(f"aciklama{i}", "") for i in range(1, 11)]
        foto_url = data.get("foto", "")

        # Satırı oluştur
        row = [tarih, ad_soyad, email] + aciklamalar + [foto_url]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print("✅ Veri Google Sheets'e eklendi:", row)

        return jsonify({"success": True, "message": "Veri başarıyla eklendi."})

    except Exception as e:
        print("🔥 Hata:", e)
        return jsonify({"success": False, "message": str(e)}), 500

# ✅ Google Sheets bağlantı testi
try:
    creds = get_creds()
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).worksheet("Sayfa1")
    sheet.append_row(["TEST", "BAĞLANTI", "OK"], value_input_option="USER_ENTERED")
    print("✅ Google Sheets test satırı eklendi.")
except Exception as e:
    print("🔥 Sheets test hatası:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Flask sunucu başlatılıyor (port {port})...")
    app.run(host="0.0.0.0", port=port, debug=True)
