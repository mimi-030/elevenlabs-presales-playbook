"""
app.py - e-commerce voice support agent (scenario 5 PoC server).

GET  /                          test storefront with the ElevenLabs Agents widget
POST /api/webhook/order_lookup  Agent tool call -> order lookup, with backend verification

Run: python app.py  ->  http://localhost:5005

Setup: create an Agent in the ElevenLabs dashboard, put its id in .env as
ELEVEN_AGENT_ID, and add a webhook tool pointing at /api/webhook/order_lookup.
For local testing you will need a tunnel (ngrok or similar) so ElevenLabs can reach
this machine.
"""
import os
from flask import Flask, render_template, jsonify, request

# Minimal dependency-free .env loader, so the repo runs with `pip install flask`.
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _fh:
        for _line in _fh:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _value = _line.partition("=")
                if _value.strip():
                    os.environ.setdefault(_key.strip(), _value.strip())

app = Flask(__name__)
AGENT_ID = os.environ.get("ELEVEN_AGENT_ID", "")

# Stand-in for the order system. In a real deployment this is a CRM or ERP call, and
# the webhook is only the middleman that authenticates and shapes the response.
ORDERS = {
    ("0912345678", "5678"): {"order_id": "#889", "status": "in transit", "eta": "tomorrow"},
    ("0987654321", "4321"): {"order_id": "#901", "status": "shipped", "eta": "Friday"},
}


@app.route("/")
def home():
    return render_template("shop.html", agent_id=AGENT_ID)


@app.route("/api/webhook/order_lookup", methods=["POST"])
def order_lookup():
    payload = request.get_json(force=True)
    phone = payload.get("phone", "")
    last4 = payload.get("last_4_digits", "")
    # The important part: identity is verified here, on the backend. Nothing the agent
    # or the browser claims about who the caller is can be trusted.
    order = ORDERS.get((phone, last4))
    if not order:
        return jsonify({"found": False,
                        "message": "No matching order. Please check the phone number "
                                   "and the last four digits."})
    return jsonify({"found": True, **order})


if __name__ == "__main__":
    if not AGENT_ID:
        print("ELEVEN_AGENT_ID is not set - the page will show setup instructions "
              "instead of the widget.")
    print("Storefront http://localhost:5005/")
    app.run(port=5005, debug=os.environ.get("FLASK_DEBUG") == "1")
