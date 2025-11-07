from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io, json, os
from datetime import datetime

app = Flask(__name__)
CORS(app)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

def get_creds():
    print("🔹 get_creds() çalışıyor...")
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("Google Sheets kimlik bilgisi bulunamadı.")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    print("✅ Google credentials yüklendi.")
    return creds

def get_sheet():
    print("🔹 get_sheet() çalışıyor...")
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    print(f"🧾 Bağlanılacak Sheet ID: {spreadsheet_id}")
    sh = client.open_by_key(spreadsheet_id)
    ws = sh.worksheet("Sayfa1")
    print("✅ Sayfa1 bulundu ve bağlanıldı.")
    return ws

def upload_to_drive(file):
    print(f"📸 upload_to_drive() çağrıldı: {file.filename}")
    creds = get_creds()
    drive_service = build("drive", "v3", credentials=creds)

    file_content = file.read()
    file.seek(0)

    file_metadata = {
        "name": f"vardiya_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    }
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=file.mimetype)

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = uploaded_file.get("id")
    print(f"✅ Dosya yüklendi, ID: {file_id}")

    # Herkese görünür yap
    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    link = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"🌐 Erişim linki: {link}")
    return link

@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        print("🟢 /api/kaydet endpoint çağrıldı.")
        tarih = request.form.get("tarih", "")
        vardiya = request.form.get("vardiya", "")
        hat = request.form.get("hat", "")
        aciklamalar_raw = request.form.get("aciklamalar", "[]")
        print("📦 Gelen veriler:", tarih, vardiya, hat, aciklamalar_raw)

        aciklamalar = json.loads(aciklamalar_raw)
        ws = get_sheet()

        for i, item in enumerate(aciklamalar):
            print(f"📝 {i+1}. açıklama işleniyor...")
            aciklama = item.get("aciklama", "")
            personel = item.get("personel", "")
            link = ""

            file = request.files.get(f"foto{i}")
            if file and file.filename:
                print(f"📤 Fotoğraf bulundu: {file.filename}")
                try:
                    link = upload_to_drive(file)
                except Exception as e:
                    print("🚫 Fotoğraf yüklenemedi:", e)
                    link = "Yüklenemedi"
            else:
                print("⚠️ Fotoğraf bulunamadı veya boş gönderildi.")

            row_data = [tarih, vardiya, hat, aciklama, personel, link]
            print(f"📄 Sheets'e eklenecek satır: {row_data}")
            ws.append_row(row_data, value_input_option="USER_ENTERED")

        print("✅ Tüm satırlar eklendi.")
        return jsonify({"mesaj": "Veriler başarıyla eklendi!"})

    except Exception as e:
        print("🔥 HATA:", e)
        return jsonify({"hata": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask sunucu başlatılıyor (port {port})...")
    app.run(host="0.0.0.0", port=port, debug=True)
