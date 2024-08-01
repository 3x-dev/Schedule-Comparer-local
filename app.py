from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import os
import pytesseract
from PIL import Image
import openai
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

openai.api_key = 'your_openai_api_key'
db = SQLAlchemy(app)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    schedule = db.Column(db.Text, nullable=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def ocr_core(filename):
    text = pytesseract.image_to_string(Image.open(filename))
    return text

def extract_schedule(text):
    response = openai.Completion.create(
        engine="davinci",
        prompt=f"Extract the class schedule from the following text:\n\n{text}",
        max_tokens=150
    )
    schedule = response.choices[0].text.strip()
    return schedule

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify', methods=['POST'])
def verify():
    if 'scheduleImage' not in request.files:
        return 'No file part', 400

    file = request.files['scheduleImage']
    if file.filename == '':
        return 'No selected file', 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        text = ocr_core(filepath)
        schedule = extract_schedule(text)

        return render_template('verify.html', name=request.form['name'], grade=request.form['grade'], schedule=schedule)

    return 'File not allowed', 400

@app.route('/confirm', methods=['POST'])
def confirm():
    name = request.form['name']
    grade = request.form['grade']
    schedule = request.form['schedule']

    new_schedule = Schedule(name=name, grade=grade, schedule=schedule)
    db.session.add(new_schedule)
    db.session.commit()

    return redirect(url_for('schedules'))

@app.route('/schedules')
def schedules():
    all_schedules = Schedule.query.all()
    return render_template('schedules.html', schedules=all_schedules)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)
