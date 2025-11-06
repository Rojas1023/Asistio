from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from database import db
from models import Event, Attendee
from s3_utils import upload_file_to_s3

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
CORS(app)

@app.before_first_request
def create_tables():
    db.create_all()


@app.route("/")
def index():
    return {"message": "Asist.io API running with Docker + RDS + S3"}


# ✅ Crear evento con imagen
@app.route("/events", methods=["POST"])
def create_event():
    title = request.form.get("title")
    description = request.form.get("description")

    if not title:
        return {"error": "title is required"}, 400

    image_url = None
    if "image" in request.files:
        image_url = upload_file_to_s3(request.files["image"])

    event = Event(title=title, description=description, image_url=image_url)
    db.session.add(event)
    db.session.commit()

    return event.to_dict(), 201


# ✅ Listar eventos
@app.route("/events", methods=["GET"])
def list_events():
    events = Event.query.order_by(Event.created_at.desc()).all()
    return jsonify([e.to_dict() for e in events])


# ✅ Detalle de evento
@app.route("/events/<int:id>", methods=["GET"])
def get_event(id):
    event = Event.query.get_or_404(id)
    return event.to_dict()


# ✅ Eliminar evento
@app.route("/events/<int:id>", methods=["DELETE"])
def delete_event(id):
    event = Event.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    return {"message": "deleted"}


# ✅ Agregar asistente
@app.route("/events/<int:event_id>/attendees", methods=["POST"])
def add_attendee(event_id):
    data = request.json
    event = Event.query.get_or_404(event_id)

    attendee = Attendee(
        event_id=event_id,
        name=data["name"],
        classification=data["classification"]
    )

    db.session.add(attendee)
    db.session.commit()

    return attendee.to_dict(), 201


# ✅ Listar asistentes
@app.route("/events/<int:event_id>/attendees", methods=["GET"])
def list_attendees(event_id):
    attendees = Attendee.query.filter_by(event_id=event_id).all()
    return jsonify([a.to_dict() for a in attendees])


# ✅ Check-in toggle
@app.route("/attendees/<int:id>/checkin", methods=["PATCH"])
def checkin(id):
    attendee = Attendee.query.get_or_404(id)
    attendee.checked_in = not attendee.checked_in
    db.session.commit()
    return attendee.to_dict()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
