from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os

app = Flask(__name__)
CORS(app)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_SHEETS_CREDENTIALS_JSON environment variable eksik!")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return creds

def get_sheet():
    creds = get_creds()
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise Exception("SPREADSHEET_ID environment variable eksik!")
    sh = client.open_by_key(spreadsheet_id)
    return sh.worksheet("Sayfa1")

@app.route("/api/kaydet", methods=["POST"])
def kaydet():
    try:
        tarih = request.form.get("tarih", "")
        vardiya = request.form.get("vardiya", "")
        hat = request.form.get("hat", "")
        aciklamalar = json.loads(request.form.get("aciklamalar", "[]"))

        ws = get_sheet()

        for item in aciklamalar:
            aciklama = item.get("aciklama", "")
            personel = item.get("personel", "")
            ws.append_row([tarih, vardiya, hat, aciklama, personel])

        return jsonify({"mesaj": "Veriler Google Sheets'e kaydedildi!"})

    except Exception as e:
        print("HATA:", e)
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
