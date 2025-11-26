from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import os, json, traceback, requests

app = Flask(__name__)
CORS(app)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ------------------------------------------
# SABİT KULLANICI (login)
# ------------------------------------------
VALID_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
VALID_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")


# ------------------------------------------
# GOOGLE SHEETS BAĞLANTI
# ------------------------------------------
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


# ------------------------------------------
# ImgBB FOTOĞRAF UPLOAD
# ------------------------------------------
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
        data = response.json()
        if data.get("success"):
            return data["data"]["url"]
        else:
            print("🚨 ImgBB Error:", data.get("error"))
            return None
    except Exception:
        print("🚨 Fotoğraf yüklenemedi:")
        traceback.print_exc()
        return None


# ------------------------------------------
# LOGIN
# ------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "message": "Kullanıcı adı veya şifre yanlış"}), 401


# ------------------------------------------
# LOGIN KONTROL FONKSİYONU
# ------------------------------------------
def check_auth():
    # frontend localStorage ile login kontrolü yapıyor, backend basit tutalım
    # isteğe bağlı: burada token veya session kontrolü ekleyebilirsin
    return True


# ---------------------------------------------------------
# ✔ VERİ EKLEME
# ---------------------------------------------------------
@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    if not check_auth():
        return jsonify({"hata": "Yetkisiz erişim"}), 401
    try:
        data = request.get_json()
        tarih = data.get("tarih")
        vardiya = data.get("vardiya")
        hat = data.get("hat")
        aciklamalar = data.get("aciklamalar", [])
        kalite_personeli = data.get("kalitePersoneli", "")

        ws = get_sheet()

        for i, item in enumerate(aciklamalar):
            aciklama = item.get("aciklama", "").strip()
            personel = item.get("personel", "").strip()
            foto_data = item.get("foto", "")

            foto_url = ""
            if foto_data:
                file_name = f"{tarih}_{vardiya}_{hat}_{i+1}_{int(os.times()[4]*1000)}"
                foto_url = upload_to_imgbb(foto_data, file_name) or "Fotoğraf yüklenemedi"

            if aciklama or personel or foto_url or kalite_personeli:
                row_index = len(ws.get_all_values()) + 1
                ws.update(f"A{row_index}:G{row_index}", [
                    [tarih, vardiya, hat, aciklama, personel, foto_url, kalite_personeli]
                ])

        return jsonify({"mesaj": "Veriler başarıyla eklendi!"}), 200

    except Exception as e:
        print("❌ Genel hata:")
        traceback.print_exc()
        return jsonify({"hata": str(e)}), 500


# ---------------------------------------------------------
# ✔ VERİ DÜZENLEME
# ---------------------------------------------------------
@app.route("/api/duzenle", methods=["POST"])
def duzenle():
    if not check_auth():
        return jsonify({"hata": "Yetkisiz erişim"}), 401
    try:
        data = request.get_json()
        row = int(data.get("row"))
        yeni = data.get("yeni")
        ws = get_sheet()

        foto_url = yeni.get("foto_url", "")
        foto_base64 = yeni.get("foto_base64", "")

        if foto_base64:
            file_name = f"edit_{row}_{int(os.times()[4]*1000)}"
            foto_url = upload_to_imgbb(foto_base64, file_name) or foto_url

        ws.update(f"A{row}:G{row}", [[
            yeni.get("tarih", ""),
            yeni.get("vardiya", ""),
            yeni.get("hat", ""),
            yeni.get("aciklama", ""),
            yeni.get("personel", ""),
            foto_url,
            yeni.get("kalitePersoneli", "")
        ]])

        return jsonify({"mesaj": "Satır başarıyla güncellendi.", "foto_url": foto_url}), 200

    except Exception as e:
        print("❌ Düzenleme hatası:")
        traceback.print_exc()
        return jsonify({"hata": str(e)}), 500


# ---------------------------------------------------------
# ✔ VERİ SİLME
# ---------------------------------------------------------
@app.route("/api/sil", methods=["POST"])
def sil():
    if not check_auth():
        return jsonify({"hata": "Yetkisiz erişim"}), 401
    try:
        data = request.get_json()
        row = int(data.get("row"))
        ws = get_sheet()
        ws.delete_rows(row)
        return jsonify({"mesaj": "Satır silindi."}), 200
    except Exception as e:
        print("❌ Silme hatası:")
        traceback.print_exc()
        return jsonify({"hata": str(e)}), 500


# ---------------------------------------------------------
# ✔ VERİ ÇEKME API (RAW JSON)
# ---------------------------------------------------------
@app.route("/api/get", methods=["GET"])
def get_data():
    try:
        ws = get_sheet()
        all_values = ws.get_all_values()

        # Başlık satırı
        header_row = all_values[0]

        # Veri satırları (başlık satırı hariç)
        full_rows = all_values[1:]

        # Data tablosu: J-O (0-index 9-14)
        data_header = header_row[9:14]
        data_rows = [r[9:15] for r in full_rows]

        # Fotoğraf tablosu: A-G (0-6)
        photo_header = header_row[0:6]
        photo_rows = [r[0:7] for r in full_rows]

        return jsonify({
            "dataHeader": data_header,
            "dataRows": data_rows,
            "photoHeader": photo_header,
            "photoRows": photo_rows
        }), 200

    except Exception as e:
        print("❌ Veri çekme hatası:")
        traceback.print_exc()
        return jsonify({"hata": str(e)}), 500




# ---------------------------------------------------------
# ✔ HEALTH CHECK
# ---------------------------------------------------------
@app.route("/health")
def health():
    return "OK", 200


# ---------------------------------------------------------
# ✔ SERVER BAŞLATMA
# ---------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
