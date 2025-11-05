from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

app = Flask(__name__)
CORS(app)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("Google Sheets kimlik bilgisi eksik.")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise Exception("SPREADSHEET_ID tanımlı değil.")
    
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")  # Sekme adın buysa değiştirmen gerekmez


@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        data = request.get_json()
        tarih = data.get("tarih")
        vardiya = data.get("vardiya")
        hat = data.get("hat")
        aciklamalar = data.get("aciklamalar", [])

        if not all([tarih, vardiya, hat]):
            return jsonify({"hata": "Tarih, vardiya ve hat zorunludur"}), 400

        ws = get_sheet()

        for a in aciklamalar:
            aciklama = a.get("aciklama", "").strip()
            personel = a.get("personel", "").strip()

            # Sadece açıklama varsa kaydet
            if aciklama:
                ws.append_row([tarih, vardiya, hat, aciklama, personel])

        return jsonify({"mesaj": "Veriler Google Sheets'e kaydedildi!"})

    except Exception as e:
        print("HATA:", str(e))
        return jsonify({"hata": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
