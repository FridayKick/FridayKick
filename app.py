import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, request, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# Initialisiere Flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Dynamischer Pfad zum Verzeichnis der App
basedir = os.path.abspath(os.path.dirname(__file__))

# MySQL-Verbindung mit SSL-Zertifikat
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://fridaykickadmin:Passw0rd!1989@fridaykicksql.mysql.database.azure.com:3306/fridaykickdb'

# SSL-Zertifikatskonfiguration für die Datenbankverbindung
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'ssl': {
            'ca': r'/home/site/wwwroot/BaltimoreCyberTrustRoot.crt.pem'
        }
    }
}



app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiere SQLAlchemy
db = SQLAlchemy(app)

# Initialisiere Flask-Migrate für die Migrationen
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Initialisiere LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Datenbankmodell für Spieler (UserMixin für Login-Kompatibilität)
class Spieler(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_attending = db.Column(db.Boolean, default=False)  # Speichert den FridayKick-Status
    is_admin = db.Column(db.Boolean, default=False)  # Admin-Rechte hinzufügen

@login_manager.user_loader
def load_user(user_id):
    return Spieler.query.get(int(user_id))

# Funktion zum Zurücksetzen der Anmeldungen
def reset_attendance():
    with app.app_context():  # Benötigt, um auf die Datenbank zuzugreifen
        Spieler.query.update({Spieler.is_attending: False})
        db.session.commit()
        print(f'Anmeldestatus wurde zurückgesetzt um {datetime.now()}')

# Starte den Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=reset_attendance, trigger='cron', day_of_week='sat', hour=18, timezone='Europe/Zurich')
scheduler.start()

# Route für die Homepage
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html', title='Home')

# Route für die Spieler-Registrierung
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Neuen Spieler zur Datenbank hinzufügen
        new_spieler = Spieler(username=username, email=email, password=hashed_password)
        db.session.add(new_spieler)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', title='Registrierung')

# Route für das Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        spieler = Spieler.query.filter_by(email=email).first()

        if spieler and check_password_hash(spieler.password, password):
            login_user(spieler)
            return redirect(url_for('dashboard'))
        flash('Ungültige Login-Daten, bitte versuchen Sie es erneut.')
    return render_template('login.html', title='Login')

# Dashboard nach Login
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

# Route zum Abmelden (Logout)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Route: FridayKick-Anmeldung (An- und Abmeldebuttons)
@app.route('/fridaykick', methods=['GET', 'POST'])
@login_required
def fridaykick():
    if request.method == 'POST':
        if 'anmelden' in request.form:
            current_user.is_attending = True
            flash('Erfolgreich für FridayKick angemeldet!', 'success')
        elif 'abmelden' in request.form:
            current_user.is_attending = False
            flash('FridayKick-Teilnahme storniert!', 'danger')
        db.session.commit()

    angemeldete_spieler = Spieler.query.filter_by(is_attending=True).all()
    abgemeldete_spieler = Spieler.query.filter_by(is_attending=False).all()

    return render_template('fridaykick.html', title='FridayKick', 
                           angemeldete_spieler=angemeldete_spieler, 
                           abgemeldete_spieler=abgemeldete_spieler)

# Starte die Anwendung
if __name__ == "__main__":
    app.run(debug=True)

# Prüfung ob Verbindung zu MySQL-Datenbank erfolgreich ist
from sqlalchemy import create_engine

# Verbindungstest
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
try:
    conn = engine.connect()
    print("Erfolgreich mit der Datenbank verbunden!")
    conn.close()
except Exception as e:
    print(f"Fehler bei der Verbindung: {e}")

