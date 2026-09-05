from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv
import json
import os
import smtplib
from email.message import EmailMessage

load_dotenv()

app = Flask(__name__)

DATA_FILE = "locations.json"

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = "sahaayon219@gmail.com"


def load_locations():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_locations(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def send_location_email(latitude, longitude, time):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return False

    msg = EmailMessage()
    msg["Subject"] = "🌌 Nebula — New Location Received"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = RECEIVER_EMAIL

    msg.set_content(
        f"""A visitor gave location permission on Nebula.

Latitude: {latitude}
Longitude: {longitude}
Time: {time}

The location was received only after the visitor granted browser location permission.
"""
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        return True

    except Exception as e:
        print("Email error:", e)
        return False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/location", methods=["POST"])
def receive_location():

    data = request.get_json(silent=True) or {}

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:
        return jsonify({
            "success": False,
            "message": "Location data missing"
        }), 400

    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    locations = load_locations()

    locations.append({
        "latitude": latitude,
        "longitude": longitude,
        "time": time
    })

    save_locations(locations)

    email_sent = send_location_email(
        latitude,
        longitude,
        time
    )

    return jsonify({
        "success": True,
        "email_sent": email_sent
    })


@app.route("/api/locations")
def get_locations():
    return jsonify(load_locations())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
