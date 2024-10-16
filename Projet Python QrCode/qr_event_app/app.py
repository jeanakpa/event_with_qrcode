from flask import Flask, render_template, request, send_file, jsonify
import qrcode
from io import BytesIO
from pyzbar.pyzbar import decode
from PIL import Image
import sqlite3
import uuid
import json

app = Flask(__name__)

def init_db():
    with sqlite3.connect('qrcodes.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS qrcodes
                     (id TEXT PRIMARY KEY, name TEXT, scanned BOOLEAN)''')

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_qr', methods=['POST'])
def generer_qr():
    nom = request.form['nom']
    qr_id = str(uuid.uuid4())
    qr_data = json.dumps({"id": qr_id, "name": nom})
    
    with sqlite3.connect('qrcodes.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO qrcodes (id, name, scanned) VALUES (?, ?, ?)", (qr_id, nom, False))
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/scanner_qr', methods=['POST'])
def scanner_qr():
    if 'qr_image' not in request.files:
        return "Aucune image n'a été téléchargée", 400
    
    qr_image = request.files['qr_image']
    img = Image.open(qr_image)
    resultat = decode(img)
    
    if resultat:
        return process_qr_data(resultat[0].data.decode('utf-8'))
    else:
        return "Aucun code QR n'a été détecté dans l'image"

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
                    return f"Ce code QR pour {nom} a déjà été scanné et ne peut plus être utilisé."
            else:
                return "Code QR non reconnu dans la base de données."
    except json.JSONDecodeError:
        return "QR code invalide : données non conformes"
    except KeyError:
        return "QR code invalide : informations manquantes"

@app.route('/view_db')
def view_db():
    with sqlite3.connect('qrcodes.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM qrcodes")
        rows = c.fetchall()
    
    return render_template('view_db.html', rows=rows)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)