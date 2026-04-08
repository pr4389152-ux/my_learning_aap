from flask import Flask, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os, zipfile
from io import BytesIO

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ultimate_secret'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ultimate.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

STYLE = """
<style>
body{background:#111;color:#fff;font-family:sans-serif;padding:10px;margin:0;}
a,button{color:#0f0;text-decoration:none;display:inline-block;margin:5px;padding:10px;border-radius:5px;background:#000;border:1px solid #0f0;cursor:pointer;}
video{width:100%;max-width:600px;}
iframe{width:100%;height:400px;border:1px solid #0f0;}
input,select{margin:5px;padding:6px;width:95%;}
</style>
"""

# ---------------- DATABASE ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    mobile = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(200))
    course = db.Column(db.String(100))
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Integer, default=0)


class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    type = db.Column(db.String(50))
    filename = db.Column(db.String(500))
    link = db.Column(db.String(500))   # ✅ NEW
    course = db.Column(db.String(100))
    order = db.Column(db.Integer)


COURSES = ["IIOT", "IR&DMT", "CNC", "Plumber", "MMV"]

# ---------------- HOME ----------------
@app.route('/')
def home():
    return STYLE + """
    <h1>ULTIMATE LEARNING</h1>
    <a href='/register'>Register</a>
    <a href='/login'>Login</a>
    <a href='/admin_login'>Admin</a>
    """

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        user = User(
            name=request.form['name'],
            email=request.form['email'],
            mobile=request.form['mobile'],
            password=generate_password_hash(request.form['password']),
            course=request.form['course']
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    options = "".join([f"<option>{c}</option>" for c in COURSES])

    return STYLE + f"""
    <h2>Register</h2>
    <form method='POST'>
    <input name='name' placeholder='Name'><br>
    <input name='email' placeholder='Email'><br>
    <input name='mobile' placeholder='Mobile'><br>
    <input type='password' name='password'><br>
    <select name='course'>{options}</select><br>
    <button>Register</button>
    </form>
    """

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user'] = user.id
            return redirect('/dashboard')
    return STYLE + """
    <h2>Login</h2>
    <form method='POST'>
    <input name='email'>
    <input type='password' name='password'>
    <button>Login</button>
    </form>
    """

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    user = User.query.get(session['user'])
    contents = Content.query.filter_by(course=user.course).all()

    html = STYLE + f"<h2>Welcome {user.name}</h2>"

    for c in contents:
        html += f"<h3>{c.title}</h3>"

        if c.type in ['theory','practical']:
            if c.link:
                html += f"<iframe src='{c.link}'></iframe>"
            else:
                html += f"<video controls src='/static/{c.filename}'></video>"

        else:
            if c.link:
                html += f"<iframe src='{c.link}'></iframe>"
                html += f"<a href='{c.link}' target='_blank'>Open</a>"
            else:
                html += f"<iframe src='/static/{c.filename}'></iframe>"
                html += f"<a href='/static/{c.filename}' download>Download</a>"

    html += "<br><a href='/logout'>Logout</a>"
    return html

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    if request.form.get('u') == 'admin' and request.form.get('p') == 'admin123':
        session['admin'] = True
        return redirect('/admin')

    return STYLE + """
    <h2>Admin Login</h2>
    <form method='POST'>
    <input name='u'>
    <input name='p' type='password'>
    <button>Login</button>
    </form>
    """

# ---------------- ADMIN PANEL ----------------
@app.route('/admin', methods=['GET','POST'])
def admin():
    if 'admin' not in session:
        return redirect('/admin_login')

    if request.method == 'POST':
        file = request.files.get('file')
        link = request.form.get('link')

        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        db.session.add(Content(
            title=request.form['title'],
            type=request.form['type'],
            filename=filename,
            link=link,
            course=request.form['course'],
            order=0
        ))
        db.session.commit()

    options = "".join([f"<option>{c}</option>" for c in COURSES])

    return STYLE + f"""
    <h2>Admin Panel</h2>

    <form method='POST' enctype='multipart/form-data'>
    <input name='title' placeholder='Title'><br>
    <select name='course'>{options}</select><br>

    <select name='type'>
    <option value='theory'>Theory</option>
    <option value='practical'>Practical</option>
    <option value='notes'>Notes</option>
    <option value='pyq'>PYQ</option>
    </select><br>

    <input name='link' placeholder='Paste Link (YouTube/Drive)'><br>
    <input type='file' name='file'><br>

    <button>Upload</button>
    </form>
    """

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
