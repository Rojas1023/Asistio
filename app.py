from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

# Config
VALID_CLASSIFICATIONS = ["Sponsor", "VIP", "Platino", "General"]

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///asistio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)  # allow access from your Flutter app origin

db = SQLAlchemy(app)


# Models
class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    location = db.Column(db.String(200), default="")
    start_datetime = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendees = db.relationship("Attendee", backref="event", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "start_datetime": self.start_datetime.isoformat() if self.start_datetime else None,
            "created_at": self.created_at.isoformat(),
            "attendees_count": len(self.attendees),
        }


class Attendee(db.Model):
    __tablename__ = "attendees"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), default="")
    classification = db.Column(db.String(50), nullable=False, default="General")
    checked_in = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "name": self.name,
            "email": self.email,
            "classification": self.classification,
            "checked_in": self.checked_in,
            "created_at": self.created_at.isoformat(),
        }


# DB initialization (create tables)
@app.before_first_request
def create_tables():
    db.create_all()


# Helpers
def parse_datetime_or_none(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def validate_classification(value):
    if value not in VALID_CLASSIFICATIONS:
        abort(jsonify({"error": f"Invalid classification. Allowed: {VALID_CLASSIFICATIONS}"}), 400)


# Routes - Events
@app.route("/events", methods=["GET"])
def list_events():
    # optional query params: ?q=keyword, ?limit=20, ?offset=0
    q = request.args.get("q", type=str)
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)

    query = Event.query.order_by(Event.start_datetime.asc().nullslast())
    if q:
        query = query.filter(Event.title.ilike(f"%{q}%"))

    events = query.offset(offset).limit(limit).all()
    return jsonify([e.to_dict() for e in events]), 200


@app.route("/events/<int:event_id>", methods=["GET"])
def get_event(event_id):
    e = Event.query.get_or_404(event_id)
    data = e.to_dict()
    # include attendees summary (not full details)
    data["attendees"] = [a.to_dict() for a in e.attendees]
    return jsonify(data), 200


@app.route("/events", methods=["POST"])
def create_event():
    payload = request.get_json(force=True)
    title = payload.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400
    description = payload.get("description", "")
    location = payload.get("location", "")
    start_dt = parse_datetime_or_none(payload.get("start_datetime"))

    new_event = Event(title=title, description=description, location=location, start_datetime=start_dt)
    db.session.add(new_event)
    db.session.commit()
    return jsonify(new_event.to_dict()), 201


@app.route("/events/<int:event_id>", methods=["PUT", "PATCH"])
def update_event(event_id):
    e = Event.query.get_or_404(event_id)
    payload = request.get_json(force=True)
    title = payload.get("title")
    if title is not None:
        e.title = title
    if "description" in payload:
        e.description = payload.get("description", "")
    if "location" in payload:
        e.location = payload.get("location", "")
    if "start_datetime" in payload:
        e.start_datetime = parse_datetime_or_none(payload.get("start_datetime"))
    db.session.commit()
    return jsonify(e.to_dict()), 200


@app.route("/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    e = Event.query.get_or_404(event_id)
    db.session.delete(e)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200


# Routes - Attendees
@app.route("/events/<int:event_id>/attendees", methods=["GET"])
def list_attendees(event_id):
    Event.query.get_or_404(event_id)  # ensure event exists
    # optional filters: ?classification=VIP, ?checked_in=true
    classification = request.args.get("classification")
    checked_in = request.args.get("checked_in")
    query = Attendee.query.filter_by(event_id=event_id)
    if classification:
        query = query.filter_by(classification=classification)
    if checked_in is not None:
        if checked_in.lower() in ("true", "1", "yes"):
            query = query.filter_by(checked_in=True)
        elif checked_in.lower() in ("false", "0", "no"):
            query = query.filter_by(checked_in=False)
    attendees = query.order_by(Attendee.created_at.asc()).all()
    return jsonify([a.to_dict() for a in attendees]), 200


@app.route("/attendees/<int:attendee_id>", methods=["GET"])
def get_attendee(attendee_id):
    a = Attendee.query.get_or_404(attendee_id)
    return jsonify(a.to_dict()), 200


@app.route("/events/<int:event_id>/attendees", methods=["POST"])
def create_attendee(event_id):
    Event.query.get_or_404(event_id)  # ensure event exists
    payload = request.get_json(force=True)
    name = payload.get("name")
    email = payload.get("email", "")
    classification = payload.get("classification", "General")
    if not name:
        return jsonify({"error": "name is required"}), 400
    if classification not in VALID_CLASSIFICATIONS:
        return jsonify({"error": f"classification must be one of {VALID_CLASSIFICATIONS}"}), 400

    a = Attendee(event_id=event_id, name=name, email=email, classification=classification)
    db.session.add(a)
    db.session.commit()
    return jsonify(a.to_dict()), 201


@app.route("/attendees/<int:attendee_id>", methods=["PUT", "PATCH"])
def update_attendee(attendee_id):
    a = Attendee.query.get_or_404(attendee_id)
    payload = request.get_json(force=True)
    if "name" in payload:
        if not payload.get("name"):
            return jsonify({"error": "name cannot be empty"}), 400
        a.name = payload.get("name")
    if "email" in payload:
        a.email = payload.get("email", "")
    if "classification" in payload:
        classification = payload.get("classification")
        if classification not in VALID_CLASSIFICATIONS:
            return jsonify({"error": f"classification must be one of {VALID_CLASSIFICATIONS}"}), 400
        a.classification = classification
    if "checked_in" in payload:
        a.checked_in = bool(payload.get("checked_in"))
    db.session.commit()
    return jsonify(a.to_dict()), 200


@app.route("/attendees/<int:attendee_id>", methods=["DELETE"])
def delete_attendee(attendee_id):
    a = Attendee.query.get_or_404(attendee_id)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200


# Check-in endpoint (toggle or set)
@app.route("/attendees/<int:attendee_id>/checkin", methods=["POST", "PATCH"])
def checkin_attendee(attendee_id):
    a = Attendee.query.get_or_404(attendee_id)
    payload = request.get_json(silent=True) or {}
    # If payload contains {"checked_in": true/false} use it; otherwise toggle
    if "checked_in" in payload:
        a.checked_in = bool(payload.get("checked_in"))
    else:
        a.checked_in = not a.checked_in
    db.session.commit()
    return jsonify(a.to_dict()), 200


# Utility endpoints
@app.route("/classifications", methods=["GET"])
def get_classifications():
    return jsonify(VALID_CLASSIFICATIONS), 200


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "Asist.io API",
        "version": "1.0",
        "endpoints": {
            "GET /events": "List events",
            "POST /events": "Create event",
            "GET /events/<id>": "Get event and its attendees",
            "PUT /events/<id>": "Update event",
            "DELETE /events/<id>": "Delete event",
            "GET /events/<id>/attendees": "List attendees for event",
            "POST /events/<id>/attendees": "Create attendee for event",
            "GET /attendees/<id>": "Get attendee",
            "PUT /attendees/<id>": "Update attendee",
            "DELETE /attendees/<id>": "Delete attendee",
            "POST /attendees/<id>/checkin": "Toggle or set checked_in",
            "GET /classifications": "Get allowed classifications"
        }
    })


# Error handler helper to ensure JSON
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(400)
def bad_request(e):
    # e may be a response object already; safe fallback
    message = getattr(e, "description", "bad request")
    return jsonify({"error": message}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
