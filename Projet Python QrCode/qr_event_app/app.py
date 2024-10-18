from flask import Flask, render_template, request, send_file, jsonify, url_for, flash, redirect, session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import qrcode
from io import BytesIO
from pyzbar.pyzbar import decode
from PIL import Image
import sqlite3
import uuid
import json
import os
import time
from flask import g

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Ajout d'une clé secrète pour les sessions
DATABASE = 'qrcodes.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    db_file = 'qrcodes.db'
    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        try:
            with sqlite3.connect(db_file) as conn:
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS qrcodes
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, scanned BOOLEAN)''')
                c.execute('''CREATE TABLE IF NOT EXISTS users
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
            print("Base de données initialisée avec succès.")
            return
        except sqlite3.DatabaseError:
            print(f"Tentative {attempt + 1}: La base de données est corrompue. Tentative de suppression...")
            try:
                conn.close()
            except:
                pass
            try:
                os.remove(db_file)
                print(f"Fichier {db_file} supprimé avec succès.")
            except PermissionError:
                print(f"Impossible de supprimer {db_file}. Fichier verrouillé.")
            except FileNotFoundError:
                print(f"Le fichier {db_file} n'existe pas.")
            
        attempt += 1
        time.sleep(1)
    
    print("Impossible d'initialiser la base de données après plusieurs tentatives.")
    raise Exception("Échec de l'initialisation de la base de données")

init_db()


# Chemin pour sauvegarder les images QR
QR_CODES_FOLDER = os.path.join(os.getcwd(), 'static', 'qrcodes')
if not os.path.exists(QR_CODES_FOLDER):
    os.makedirs(QR_CODES_FOLDER)


def nom_exist(nom):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM qrcodes WHERE name = ?", (nom,))
        return c.fetchone() is not None



@app.route('/generer_qr', methods=['POST'])
def generer_qr():
    nom = request.form['nom'].strip().upper()
    
    if nom_exist(nom):
        return jsonify({"error": "Ce nom est déjà enregistré."}), 400
    
    with sqlite3.connect('qrcodes.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO qrcodes (name, scanned) VALUES (?, ?)", (nom, False))
        qr_id = c.lastrowid

    qr_data = json.dumps({"id": qr_id, "name": nom})
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    QR_CODES_FOLDER = os.path.join(os.getcwd(), 'static', 'qrcodes')
    if not os.path.exists(QR_CODES_FOLDER):
        os.makedirs(QR_CODES_FOLDER)
    qr_image_path = os.path.join(QR_CODES_FOLDER, f'{qr_id}.png')
    img.save(qr_image_path)
    

    return jsonify({
        "success": True,
        "message": f"{nom} a été enregistré avec succès.",
        "qr_code": f"/qr_image/{qr_id}"
    }), 200



@app.route('/scanner_qr_camera', methods=['POST'])
def scanner_qr_camera():
    data = request.json
    return process_qr_data(data['qr_data'])



def process_qr_data(qr_data):
    try:
        qr_info = json.loads(qr_data)
        qr_id = qr_info["id"]
        nom = qr_info["name"]
        
        with sqlite3.connect('qrcodes.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM qrcodes WHERE id = ?", (qr_id,))
            qr_db_data = c.fetchone()
            
            if qr_db_data:
                if not qr_db_data[2]:  # Si pas encore scanné
                    c.execute("UPDATE qrcodes SET scanned = TRUE WHERE id = ?", (qr_id,))
                    return f"{nom} est marqué présent"
                else:
                    return f"{nom} est deja present"
            else:
                return "Code QR non reconnu dans la base de données."
    except json.JSONDecodeError:
        return "QR code invalide : données non conformes"
    except KeyError:
        return "QR code invalide : informations manquantes"


@app.route('/qr_image/<int:qr_id>')
def afficher_qr(qr_id):
    qr_image_path = os.path.join(QR_CODES_FOLDER, f'{qr_id}.png')
    
    if os.path.exists(qr_image_path):
        return send_file(qr_image_path, mimetype='image/png')
    else:
        return "QR code introuvable", 404


@app.route('/view_db')
def view_db():
    try:
        with sqlite3.connect('qrcodes.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM qrcodes")
            rows = c.fetchall()
            
            # Calculer les statistiques
            total = len(rows)
            scanned = sum(1 for row in rows if row[2])  # row[2] est le champ 'scanned'
            non_scanned = total - scanned
            
            stats = {
                'total': total,
                'scanned': scanned,
                'non_scanned': non_scanned
            }
        
        print("Debug - Stats:", stats)  # Ajoutez cette ligne pour le débogage
        
        return render_template('view_db.html', rows=rows, stats=stats)
    except Exception as e:
        print(f"Erreur lors de l'accès à la base de données : {str(e)}")
        return render_template('view_db.html', rows=[], stats={'total': 0, 'scanned': 0, 'non_scanned': 0})


@app.route('/effacer_db', methods=['GET'])

def effacer_db():
    with sqlite3.connect('qrcodes.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM qrcodes")
        conn.commit()
    return "Toutes les données ont été effacées de la base de données.", 200


@app.route('/supprimer/<int:qr_id>', methods=['DELETE'])
def supprimer(qr_id):
    with sqlite3.connect('qrcodes.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM qrcodes WHERE id = ?", (qr_id,))
        conn.commit()
    
    return jsonify({
        "success": True,
        "message": "Enregistrement supprimé définitivement avec succès."
    }), 200


def get_user_by_email(email):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        
        if user and check_password_hash(user[2], password):  # user[2] est le champ du mot de passe haché
            session['user_id'] = user[0]  # Stocker l'ID de l'utilisateur dans la session
            flash('Connexion réussie !', 'success')
            return redirect(url_for('home'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Fonction pour ajouter un utilisateur (à utiliser pour l'inscription ou par un administrateur)
def add_user(email, password):
    hashed_password = generate_password_hash(password)
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
        conn.commit()

@app.route('/')
@login_required
def home():
    return render_template('index.html')



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
