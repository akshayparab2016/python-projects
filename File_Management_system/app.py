from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask import abort
import os
from datetime import datetime 

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ======================= CONFIG =======================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {
    # Images
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg',
    # Documents
    'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    # Code files
    'py', 'js', 'html', 'css', 'json', 'xml', 'csv',
    # Archives
    'zip', 'rar', '7z', 'tar', 'gz',
    # Audio
    'mp3', 'wav', 'ogg',
    # Video
    'mp4', 'mkv', 'avi', 'mov', 'webm'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ======================= DATABASE MODEL =======================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ======================= HELPERS =======================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('🔒 Login required!')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ======================= AUTH =======================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('⚠️ User already exists!')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)

            db.session.add(new_user)
            db.session.commit()

            os.makedirs(os.path.join(UPLOAD_FOLDER, username), exist_ok=True)

            flash('✅ Registered successfully! Please login.')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('✅ Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid credentials!')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('👋 Logged out!')
    return redirect(url_for('login'))

# ======================= DASHBOARD =======================

@app.route('/')
@login_required
def dashboard():
    user_folder = os.path.join(UPLOAD_FOLDER, session['username'])

    files = os.listdir(user_folder)

    files = sorted(
        files,
        key=lambda x: os.path.getmtime(os.path.join(user_folder, x)),
        reverse=True
    )

    file_data = []
    for file in files:
        path = os.path.join(user_folder, file)
        timestamp = os.path.getmtime(path)

        file_data.append({
            "name": file,
            "time": timestamp
        })

    return render_template(
        'dashboard.html',
        files=file_data,
        user=session['username']
    )

# ======================= FILE OPERATIONS =======================

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    user_folder = os.path.join(UPLOAD_FOLDER, session['username'])

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(user_folder, filename))
        flash('📤 File uploaded!')
    else:
        flash('❌ Invalid OR blank file!')

    return redirect(url_for('dashboard'))


@app.route('/download/<filename>')
@login_required
def download(filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, session['username']), filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['POST'])
@login_required
def delete(filename):
    user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
    path = os.path.join(user_folder, filename)

    if not os.path.isfile(path):
        abort(404)

    os.remove(path)
    flash('🗑️ Deleted successfully!')
    return redirect(url_for('dashboard'))


@app.route('/view/<filename>')
@login_required
def view(filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, session['username']), filename)


@app.template_filter('datetimeformat')
def datetimeformat(value):
    now = datetime.now()
    diff = now - datetime.fromtimestamp(value)

    if diff.seconds < 60:
        return "Just now"
    elif diff.seconds < 3600:
        return f"{diff.seconds // 60} min ago"
    else:
        return datetime.fromtimestamp(value).strftime('%d %b %Y, %I:%M %p')
# ======================= INIT =======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()   
    app.run()