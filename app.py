from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os

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
    return sh.sheet1

@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        data = request.get_json()
        if not all([data.get("tarih"), data.get("vardiya"), data.get("hat"), data.get("aciklama"), data.get("personel")]):
            return jsonify({"hata": "Lütfen tüm alanları doldurun"}), 400

        ws = get_sheet()
        ws.append_row([data["tarih"], data["vardiya"], data["hat"], data["aciklama"], data["personel"]])
        return jsonify({"mesaj": "Veri Google Sheets'e kaydedildi!"})

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
