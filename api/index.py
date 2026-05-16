from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "service": "chatbot-api",
        "status": "ok"
    })

@app.route("/api/health")
def health():
    return jsonify({
        "message": "API is working"
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    message = data.get("message")

    return jsonify({
        "user_message": message,
        "bot_reply": "Hello from Flask on Vercel"
    })
