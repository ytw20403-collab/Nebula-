from flask import Flask, render_template, jsonify
from datetime import datetime
from dotenv import load_dotenv
import os
import smtplib
from email.message import EmailMessage
import psycopg2

load_dotenv()

app = Flask(__name__)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = "sahaayon219@gmail.com"

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            time TIMESTAMP NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def load_locations():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT latitude, longitude, time
        FROM locations
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    locations = []

    for row in rows:
        locations.append({
            "latitude": row[0],
            "longitude": row[1],
            "time": row[2].strftime("%Y-%m-%d %H:%M:%S")
        })

    return locations


def save_location(latitude, longitude, time):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO locations (latitude, longitude, time)
        VALUES (%s, %s, %s)
    """, (latitude, longitude, time))

    conn.commit()

    cur.close()
    conn.close()


def send_location_email(latitude, longitude, time):

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Gmail configuration missing.")
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

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        print("Email sent successfully.")
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

    from flask import request

    data = request.get_json(silent=True) or {}

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Location data missing"
        }), 400

    time = datetime.now()

    try:

        # First save location permanently in PostgreSQL
        save_location(
            latitude,
            longitude,
            time
        )

        print("Location saved to PostgreSQL.")

    except Exception as e:

        print("Database error:", e)

        return jsonify({
            "success": False,
            "message": "Location could not be saved"
        }), 500

    # Email failure will NOT delete/fail the saved location
    email_sent = send_location_email(
        latitude,
        longitude,
        time.strftime("%Y-%m-%d %H:%M:%S")
    )

    return jsonify({
        "success": True,
        "email_sent": email_sent
    })


@app.route("/api/locations")
def get_locations():

    try:

        locations = load_locations()

        return jsonify(locations)

    except Exception as e:

        print("Database read error:", e)

        return jsonify({
            "error": "Could not load locations"
        }), 500


# Create PostgreSQL table when the application starts
try:

    init_db()
    print("PostgreSQL database ready.")

except Exception as e:

    print("Database initialization error:", e)


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080
    )
