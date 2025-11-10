from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import traceback

app = Flask(__name__)
CORS(app)

# 🔑 ImgBB API key’i environment variable’dan al
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")

if not IMGBB_API_KEY:
    raise Exception("IMGBB_API_KEY environment variable bulunamadı!")

# 📸 Fotoğraf yükleme endpoint’i
@app.route("/api/upload", methods=["POST"])
def upload():
    try:
        data = request.get_json()
        base64_image = data.get("foto", "")
        file_name = data.get("name", "test_image")

        if not base64_image.startswith("data:image"):
            return jsonify({"error": "Geçersiz base64 formatı"}), 400

        # Saf base64 kısmını al
        if "," not in base64_image:
            return jsonify({"error": "Base64 verisi hatalı"}), 400

        image_bytes = base64_image.split(",")[1]
        print("Base64 uzunluğu:", len(image_bytes))
        print("Payload gönderiliyor...")

        payload = {
            "key": IMGBB_API_KEY,
            "image": image_bytes,
            "name": file_name
        }

        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        print("Status code:", response.status_code)
        print("Response:", response.text)

        result = response.json()
        if result.get("success"):
            return jsonify({"url": result["data"]["url"]})
        else:
            return jsonify({"error": result.get("error", {}).get("message", "Bilinmeyen hata")}), 400

    except Exception:
        print("🚨 Upload sırasında hata:")
        traceback.print_exc()
        return jsonify({"error": "Sunucu hatası"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
