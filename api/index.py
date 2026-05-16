from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/")
def home():
    return jsonify({
        "service": "chatbot-api",
        "status": "ok"
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "working"})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    message = data.get("message", "")

    return jsonify({
        "message": message,
        "reply": "Hello from Flask"
    })