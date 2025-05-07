from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///main.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_key")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)    

class Exo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Personal_record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer)
    time = db.Column(db.String(100))
    added_weight = db.Column(db.Float)
    date = db.Column(db.String(100))
    exo_id = db.Column(db.Integer, db.ForeignKey('exo.id', name='fk_personal_record_exo_id'), nullable=False)
    exo = db.relationship('Exo')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_personal_record_user_id'), nullable=False)
    user = db.relationship('User')
    weight = db.Column(db.Integer)
    bodyweight = db.Column(db.Float)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token manquant"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = User.query.get(data["user_id"])
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            return jsonify({"message": f"Token invalide : {str(e)}"}), 401

        return f(current_user, *args, **kwargs)

    return decorated

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"message": "Champs manquants"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email déjà utilisé"}), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Utilisateur créé avec succès"}), 201
    
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"message": "Champs manquants"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"message": "Identifiants invalides"}), 401

    token = generate_token(user.id)
    return jsonify({"message": "Connexion réussie", "token": token}), 200

@app.route("/exo", methods=["GET"])
def get_exo():
    exo = Exo.query.all()
    result = []

    for i in exo:
        result.append({
            "id": i.id,
            "name": i.name
        })
    return jsonify(result)    

@app.route("/exo", methods=["POST"])
def add_exo():
    data = request.get_json()
    exo = Exo(name=data["name"])

    db.session.add(exo)
    db.session.commit()
    return jsonify({"message": "Exo ajouté avec succès."}), 201

@app.route("/personal_record", methods=["GET"])
@token_required
def get_personal_record(current_user):
    pr = Personal_record.query.filter_by(user_id=current_user.id)
    result = []

    for i in pr:
        result.append({
            "id": i.id,
            "quantity": i.quantity,
            "added_weight": i.added_weight,
            "date": i.date,
            "weight": i.weight,
            "bodyweight": i.bodyweight
        })
    return jsonify(result)        

@app.route("/personal_record", methods=["POST"])
@token_required
def add_personal_record(current_user):
    data = request.get_json()

    if not all(key in data for key in ["exo_id", "quantity", "time", "added_weight", "date", "weight"]):
            return jsonify({"message": "Données invalides; champs manquants"}), 400

    bodyweight = round((data["weight"]+data["added_weight"])/data["weight"],3)*100

    pr = Personal_record(exo_id=data["exo_id"], user_id=current_user.id, quantity=data["quantity"], time=data["time"], added_weight=data["added_weight"], date=data["date"], weight=data["weight"], bodyweight=bodyweight)

    db.session.add(pr)
    db.session.commit()
    return jsonify({"message": "PR ajouté avec succès."}), 201

@app.route("/personal_record", methods=["DELETE"])
@token_required
def del_personal_record(current_user):
    data = request.get_json()

    Personal_record.query.filter_by(user_id=current_user.id, id=data["id"]).delete()
    db.session.commit()

    return jsonify({"message": "PR supprimé avec succès"}), 201

if __name__ == "__main__":
    #with app.app_context():
        #db.create_all()
    app.run(debug=True)
