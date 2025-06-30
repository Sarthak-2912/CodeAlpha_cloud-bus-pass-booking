from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Ticket(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_name = db.Column(db.String(100))
    route = db.Column(db.String(100))
    price = db.Column(db.Float)
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)
