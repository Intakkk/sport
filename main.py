from flask import Flask, request, jsonify, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from flask_migrate import Migrate
import os
import requests
from urllib.parse import urlencode

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///main.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_key")
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")

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
    pr = db.Column(db.String(100))
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

class StravaActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_stravaactivity_user_id'), nullable=False)
    user = db.relationship('User')
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)

class HeartRateSample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('strava_activity.id'), nullable=False)
    activity = db.relationship('StravaActivity',backref=db.backref('samples', lazy=True))
    hr = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Integer, nullable=False)

class StravaToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_strava_token_user_id'), nullable=False)
    user = db.relationship('User')
    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)
    strava_athlete_id = db.Column(db.Integer, nullable=True)

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

def fetch_strava_activities(current_user):
    token = StravaToken.query.filter_by(user_id=current_user.id).first()

    if not token:
        return {"message": "Token Strava manquant"}, 400

    # Vérifie si le token est expiré
    if token.expires_at < datetime.datetime.utcnow().timestamp():
        refresh_response = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token
        })
        if refresh_response.status_code != 200:
            return {"message": "Erreur lors du refresh du token"}, 400

        new_tokens = refresh_response.json()
        token.access_token = new_tokens["access_token"]
        token.refresh_token = new_tokens["refresh_token"]
        token.expires_at = new_tokens["expires_at"]
        db.session.commit()

    # Appel à l’API Strava pour récupérer les activités
    headers = {"Authorization": f"Bearer {token.access_token}"}
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    params = {"per_page": 5, "page": 1}
    response = requests.get(activities_url, headers=headers, params=params)

    if response.status_code != 200:
        return {"message": "Erreur API Strava"}, 400

    activities = response.json()
    nombre_activite=len(activities)
    for act in activities:
        # Ne stocke que les nouvelles activités
        if not StravaActivity.query.filter_by(strava_id=act["id"]).first():
            new_act = StravaActivity(
                strava_id=act["id"],
                user_id=current_user.id,
            )
            db.session.add(new_act)
            db.session.flush() # pour obtenir new_act.id avant le commit
            
            activity_id = act["id"]
            hr_stream_url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
            hr_params = {"keys": "heart_rate,time", "key_by_type": "true"}
            hr_response = requests.get(hr_stream_url, headers=headers, params=hr_params)

            if hr_response.status_code == 200:
                hr_stream = hr_response.json()
                if "heart_rate" in hr_stream and "time" in hr_stream:
                    hr_values = hr_stream["heart_rate"]["data"]
                    time_values = hr_stream["time"]["data"]
                    for hr, t in zip(hr_values, time_values):
                        sample = HeartRateSample(
                            activity_id=new_act.id,
                            hr=hr,
                            time=t
                        )
                        db.session.add(sample)

    db.session.commit()
    return {"message": "Activités Strava mises à jour",
            "nombres d'activités": {nombre_activite}}

@app.route("/")
def index():
    return render_template("index.html")

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

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

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

@app.route("/personal-index")
def personal_index():
    return render_template("personal_index.html")

@app.route("/pr-types", methods=["GET"])
@token_required
def get_pr_types(current_user):
    pr_types = db.session.query(Personal_record.pr, Exo.name).filter_by(user_id=current_user.id).join(Personal_record.exo).distinct().all()
    result = [
        {"pr": pr, "exercise": exo_name}
        for pr, exo_name in pr_types
    ]
    return jsonify(result)

@app.route("/activities", methods=["GET"])
@token_required
def get_activities(current_user):
    activities = db.session.query(StravaActivity.strava_id).filter_by(user_id=current_user.id).distinct().all()
    return jsonify([act[0] for act in activities])

@app.route("/personal-record/<pr_type>/<exo_name>")
def personal_record(pr_type, exo_name):
    return render_template("personal_record.html", pr_type=pr_type, exo_name=exo_name)

@app.route("/get-personal-record/<pr_type>/<exo_name>", methods=["GET"])
@token_required
def get_personal_record(current_user, pr_type, exo_name):
    print("PR type reçu:", pr_type)
    print("Nom exo reçu:", exo_name)
    pr = db.session.query(Personal_record).join(Exo).filter(Personal_record.user_id==current_user.id, Personal_record.pr==pr_type, Exo.name==exo_name).order_by(Personal_record.date.asc()).all()
    result = []

    for i in pr:
        result.append({
            "quantity": i.quantity,
            "time": i.time,
            "added_weight": i.added_weight,
            "date": i.date,
            "weight": i.weight,
            "bodyweight": i.bodyweight
        })
    return jsonify(result)        

@app.route("/personal-record-add")
def personal_record_add():
    return render_template("personal_record_add.html")

@app.route("/personal-record", methods=["POST"])
@token_required
def add_personal_record(current_user):
    data = request.get_json()
    print(data)
    if not all(key in data for key in ["exo_id", "pr", "quantity", "time", "added_weight", "date", "weight"]):
            return jsonify({"message": "Données invalides; champs manquants"}), 400

    if data["weight"] != None and data["added_weight"] != None:
        bodyweight = round((data["weight"]+data["added_weight"])/data["weight"],3)*100
    else:
        bodyweight = None
    print(bodyweight)
    pr = Personal_record(exo_id=data["exo_id"], user_id=current_user.id, pr=data["pr"],quantity=data["quantity"], time=data["time"], added_weight=data["added_weight"], date=data["date"], weight=data["weight"], bodyweight=bodyweight)

    db.session.add(pr)
    db.session.commit()
    return jsonify({"message": "PR ajouté avec succès."}), 201

@app.route("/personal-record", methods=["DELETE"])
@token_required
def del_personal_record(current_user):
    data = request.get_json()

    Personal_record.query.filter_by(user_id=current_user.id, id=data["id"]).delete()
    db.session.commit()

    return jsonify({"message": "PR supprimé avec succès"}), 201

@app.route("/strava/<int:stravaid>")
def graph_activity(stravaid):
    return render_template("strava_activity.html", stravaid=stravaid)

@app.route("/strava/login", methods=["GET"])
def strava_login():
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "redirect_uri": STRAVA_REDIRECT_URI,
        "response_type": "code",
        "scope": "activity:read_all",
    }

    strava_auth_url = f"https://www.strava.com/oauth/authorize?{urlencode(params)}"
    return redirect(strava_auth_url)

@app.route("/strava/callback")
def strava_callback():
    code = request.args.get("code")

    if not code:
        return jsonify({"message": "Code manquant"}), 400

    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    if response.status_code != 200:
        return jsonify({"message": "Erreur récupération token"}), 400

    tokens = response.json()

    existing_token = StravaToken.query.filter_by(user_id=1).first()
    if existing_token:
        existing_token.access_token = tokens["access_token"]
        existing_token.refresh_token = tokens["refresh_token"]
        existing_token.expires_at = tokens["expires_at"]
    else:
        new_token = StravaToken(
            user_id=1,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_at=tokens["expires_at"],
            strava_athlete_id=tokens.get("athlete", {}).get("id")
        )
        db.session.add(new_token)

    db.session.commit()

    return jsonify({"message": "Token Strava enregistré avec succès."})

@app.route("/strava/sync", methods=["GET"])
def sync_strava():
    current_user=User.query.get(1)
    result = fetch_strava_activities(current_user)
    return jsonify(result)

if __name__ == "__main__":
    #with app.app_context():
        #db.create_all()
    app.run(debug=True)
