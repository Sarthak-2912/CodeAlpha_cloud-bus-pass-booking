from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config
from models import db, Ticket
import uuid
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image
import qrcode
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
CORS(app)

# Create static/qr directory if it doesn't exist
os.makedirs("static/qr", exist_ok=True)

FARES = {
    "Kashmere Gate": {"ISBT Anand Vihar": 20, "Rajiv Chowk": 15, "Karol Bagh": 20, "Connaught Place": 15},
    "ISBT Anand Vihar": {"Kashmere Gate": 20, "Lajpat Nagar": 30, "Nehru Place": 35, "Okhla": 40},
    "Rajiv Chowk": {"Kashmere Gate": 15, "AIIMS": 25, "Connaught Place": 10, "Hauz Khas": 35},
    "Lajpat Nagar": {"ISBT Anand Vihar": 30, "AIIMS": 20, "Saket": 25, "Nehru Place": 15},
    "Saket": {"Lajpat Nagar": 25, "Hauz Khas": 20, "Vasant Vihar": 30, "Okhla": 35},
    "Dwarka Sector 21": {"Janakpuri": 25, "Vasant Vihar": 35, "Rohini West": 50},
    "Nehru Place": {"Lajpat Nagar": 15, "AIIMS": 20, "Okhla": 20},
    "AIIMS": {"Rajiv Chowk": 25, "Nehru Place": 20, "Lajpat Nagar": 20},
    "Hauz Khas": {"Rajiv Chowk": 35, "Saket": 20, "Vasant Vihar": 20},
    "Rohini West": {"Dwarka Sector 21": 50, "Karol Bagh": 25, "Janakpuri": 30},
    "Karol Bagh": {"Rohini West": 25, "Kashmere Gate": 20},
    "Connaught Place": {"Rajiv Chowk": 10, "Kashmere Gate": 15},
    "Vasant Vihar": {"Dwarka Sector 21": 35, "Hauz Khas": 20, "Saket": 30},
    "Janakpuri": {"Dwarka Sector 21": 25, "Rohini West": 30},
    "Okhla": {"ISBT Anand Vihar": 40, "Nehru Place": 20, "Saket": 35}
}

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/book', methods=['POST'])
def book_ticket():
    data = request.json
    source = data['source']
    destination = data['destination']
    passengers = int(data['passengers'])
    if source == destination:
        return jsonify({"error": "Source and destination cannot be the same"}), 400
    try:
        base_fare = FARES[source][destination]
    except KeyError:
        return jsonify({"error": "Invalid route selected"}), 400
    total_fare = base_fare * passengers
    ticket_id = str(uuid.uuid4())
    ticket = Ticket(id=ticket_id, user_name=data['user'], route=f"{source} → {destination}", price=total_fare)
    db.session.add(ticket)
    db.session.commit()

    # Generate QR Code
    qr = qrcode.make(f"Ticket ID: {ticket_id}\nName: {ticket.user_name}\nRoute: {ticket.route}\nFare: ₹{total_fare}")
    qr_path = f"static/qr/{ticket_id}.png"
    qr.save(qr_path)

    return jsonify({
        "message": "Ticket booked!",
        "ticket_id": ticket_id,
        "route": ticket.route,
        "passengers": passengers,
        "fare": total_fare,
        "qr_path": "/" + qr_path  # relative path for frontend display
    })

@app.route('/download/<ticket_id>')
def download(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return "Ticket not found", 404

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.drawString(100, 800, "🚌 Cloud Bus Ticket")
    p.drawString(100, 770, f"Ticket ID: {ticket.id}")
    p.drawString(100, 750, f"Name: {ticket.user_name}")
    p.drawString(100, 730, f"Route: {ticket.route}")
    p.drawString(100, 710, f"Total Fare: ₹{ticket.price}")

    qr_path = f"static/qr/{ticket.id}.png"
    if os.path.exists(qr_path):
        p.drawInlineImage(qr_path, 100, 580, width=120, height=120)

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"ticket_{ticket.id}.pdf", mimetype='application/pdf')

@app.route('/admin')
def admin_dashboard():
    tickets = Ticket.query.all()
    total_tickets = len(tickets)
    total_revenue = sum(t.price for t in tickets)
    return render_template('admin.html', tickets=tickets, total_tickets=total_tickets, total_revenue=total_revenue)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
