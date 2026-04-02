from flask import Flask, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
from reportlab.pdfgen import canvas
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
a,button{color:#0f0;text-decoration:none;display:inline-block;margin:5px;padding:10px 15px;border-radius:5px;background:#000;border:1px solid #0f0;cursor:pointer;}
video{width:100%;max-width:600px;height:auto;margin:10px 0;}
iframe{border:1px solid #0f0;border-radius:5px;margin:5px 0;}
details{margin:10px 0;padding:10px;border:1px solid #0f0;border-radius:5px;}
summary{font-weight:bold;cursor:pointer;padding:5px;}
textarea,input,select{margin:5px;padding:6px;border-radius:5px;border:none;width:95%;}
@media(max-width:600px){body{padding:5px;}a,button{width:100%;text-align:center;}}
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
    type = db.Column(db.String(50))  # 'theory','practical','notes','pyq'
    filename = db.Column(db.String(500))
    course = db.Column(db.String(100))
    order = db.Column(db.Integer)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100))
    question = db.Column(db.String(300))
    op1 = db.Column(db.String(100))
    op2 = db.Column(db.String(100))
    op3 = db.Column(db.String(100))
    op4 = db.Column(db.String(100))
    answer = db.Column(db.String(100))


COURSES = ["IIOT", "IR&DMT", "CNC", "Plumber", "MMV"]


# ---------------- HOME ----------------
@app.route('/')
def home():
    return STYLE + """
    <h1>🚀 ULTIMATE LEARNING PLATFORM</h1>
    <a href='/register'>Register</a> | 
    <a href='/login'>Login</a> | 
    <a href='/leaderboard'>Leaderboard</a> | 
    <a href='/admin_login'>Admin</a>
    """


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form['email']).first() or User.query.filter_by(
                mobile=request.form['mobile']).first():
            return STYLE + "<p>Email or Mobile already registered!</p><a href='/register'>Back</a>"
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
    <input type='password' name='password' placeholder='Password'><br>
    <select name='course'>{options}</select><br>
    <button>Register</button>
    </form>
    """


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['login_id']
        password = request.form['password']
        user = User.query.filter((User.email == login_id) | (User.mobile == login_id)).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.id
            return redirect('/dashboard')
        else:
            return STYLE + "<p>Invalid login!</p><a href='/login'>Back</a>"
    return STYLE + """
    <h2>Login</h2>
    <form method='POST'>
    <input name='login_id' placeholder='Email or Mobile'><br>
    <input type='password' name='password' placeholder='Password'><br>
    <button>Login</button>
    </form>
    """


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    user = User.query.get(session['user'])
    contents = Content.query.filter_by(course=user.course).order_by(Content.order).all()

    html = STYLE + f"<h2>Welcome {user.name}</h2>"
    html += f"<p>Course: {user.course} | Progress: {user.progress}% | Score: {user.score}</p><hr>"

    types = {'theory': [], 'practical': [], 'notes': [], 'pyq': []}
    for c in contents:
        types[c.type].append(c)

    for t, label in [('theory', 'Theory Videos'), ('practical', 'Practical Videos'), ('notes', 'Notes PDFs'),
                     ('pyq', 'PYQs PDFs')]:
        html += f"<details><summary>{label}</summary>"
        if types[t]:
            for c in types[t]:
                if t in ['theory', 'practical']:
                    html += f"<p>{c.title}</p>"
                    html += f"<video controls><source src='/static/{c.filename}' type='video/mp4'>Your browser does not support the video tag.</video><br>"
                else:
                    html += f"<p>{c.title}</p>"
                    html += f"<iframe src='/static/{c.filename}' width='100%' height='600px'></iframe><br>"
                    html += f"<a href='/static/{c.filename}' download>Download PDF</a><br>"
        else:
            html += "<p>No content available.</p>"
        html += "</details><br>"

    html += f"<button onclick=\"location.href='/download_all'\">Download All PDFs</button><br>"
    html += "<a href='/leaderboard'>Leaderboard</a><br>"
    html += "<a href='/logout'>Logout</a>"
    return html


# ---------------- DOWNLOAD ALL PDFs ----------------
@app.route('/download_all')
def download_all():
    if 'user' not in session:
        return redirect('/login')
    user = User.query.get(session['user'])
    contents = Content.query.filter(Content.course == user.course, Content.type.in_(['notes', 'pyq'])).all()

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for c in contents:
            file_path = os.path.join(UPLOAD_FOLDER, c.filename)
            if os.path.exists(file_path):
                zf.write(file_path, arcname=c.filename)
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{user.course}_resources.zip", as_attachment=True)


# ---------------- LEADERBOARD ----------------
@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.score.desc()).all()
    html = STYLE + "<h2>Leaderboard</h2>"
    for u in users:
        html += f"<p>{u.name} - {u.score}</p>"
    html += "<a href='/dashboard'>Dashboard</a>"
    return html


# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['u'] == 'admin' and request.form['p'] == 'admin123':
            session['admin'] = True
            return redirect('/admin')
    return STYLE + """
    <h2>Admin Login</h2>
    <form method='POST'>
    <input name='u' placeholder='Username'><br>
    <input name='p' placeholder='Password' type='password'><br>
    <button>Login</button>
    </form>
    """


# ---------------- ADMIN PANEL ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect('/admin_login')
    if request.method == 'POST':
        # Single content (PDF) upload
        title = request.form.get('title')
        course = request.form.get('course')
        order = request.form.get('order', 0)
        file = request.files.get('file')
        content_type = request.form.get('type')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            db.session.add(Content(title=title, type=content_type, filename=filename, course=course, order=int(order)))

        # Multiple videos upload
        if 'files' in request.files:
            files = request.files.getlist('files')
            video_type = request.form.get('type')
            course = request.form.get('course')
            order = 0
            for f in files:
                if f.filename:
                    filename = secure_filename(f.filename)
                    f.save(os.path.join(UPLOAD_FOLDER, filename))
                    db.session.add(
                        Content(title=filename, type=video_type, filename=filename, course=course, order=order))
                    order += 1
        db.session.commit()

    options = "".join([f"<option>{c}</option>" for c in COURSES])

    # Display uploaded content with delete option
    all_contents = Content.query.order_by(Content.course, Content.type, Content.order).all()
    content_html = ""
    for c in all_contents:
        content_html += f"<p>{c.course} - {c.type} - {c.title} "
        content_html += f"<a href='/delete_content/{c.id}' onclick=\"return confirm('Delete?')\">Delete</a></p>"

    return STYLE + f"""
    <h2>ADMIN PANEL</h2>

    <h3>Upload Single Content (PDF)</h3>
    <form method='POST' enctype='multipart/form-data'>
    <input name='title' placeholder='Title'><br>
    <select name='course'>{options}</select><br>
    <select name='type'>
        <option value='notes'>Notes PDF</option>
        <option value='pyq'>PYQs PDF</option>
    </select><br>
    <input name='order' placeholder='Order'><br>
    <input type='file' name='file'><br>
    <button>Upload</button>
    </form>

    <h3>Upload Multiple Videos (Theory/Practical)</h3>
    <form method='POST' enctype='multipart/form-data'>
    <select name='course'>{options}</select><br>
    <select name='type'>
        <option value='theory'>Theory Video</option>
        <option value='practical'>Practical Video</option>
    </select><br>
    <input type='file' name='files' multiple><br>
    <button>Upload Videos</button>
    </form>

    <h3>All Uploaded Content</h3>
    {content_html}
    """


# ---------------- DELETE CONTENT ----------------
@app.route('/delete_content/<int:id>')
def delete_content(id):
    if 'admin' not in session:
        return redirect('/admin_login')
    content = Content.query.get(id)
    if content:
        file_path = os.path.join(UPLOAD_FOLDER, content.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(content)
        db.session.commit()
    return redirect('/admin')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------- CREATE DB & RUN ----------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)