from database import db
from datetime import datetime

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendees = db.relationship("Attendee", backref="event", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat(),
            "attendees_count": len(self.attendees)
        }


class Attendee(db.Model):
    __tablename__ = "attendees"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    name = db.Column(db.String(200), nullable=False)
    classification = db.Column(db.String(50))
    checked_in = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "name": self.name,
            "classification": self.classification,
            "checked_in": self.checked_in,
            "created_at": self.created_at.isoformat(),
        }
