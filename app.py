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
    data = request.get_json()
    tarih = data.get("tarih")
    vardiya = data.get("vardiya")
    hat = data.get("hat")
    aciklama = data.get("aciklama")
    personel = data.get("personel")

    if not all([tarih, vardiya, hat, aciklama, personel]):
        return jsonify({"hata": "Lütfen tüm alanları doldurun"}), 400

    ws = get_sheet()
    ws.append_row([tarih, vardiya, hat, aciklama, personel])
    return jsonify({"mesaj": "Veri Google Sheets'e kaydedildi!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
