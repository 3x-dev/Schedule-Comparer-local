from flask import Flask, request, render_template, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os
import base64
import json
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

db = SQLAlchemy(app)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    schedule = db.Column(db.Text, nullable=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def load_json_schema(schema_file: str) -> dict:
    with open(schema_file, 'r') as file:
        return json.load(file)

def get_gpt_response(image_path, schema):
    with open(image_path, 'rb') as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    response = client.chat.completions.create(
        model='gpt-4o',
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Provide a JSON file that represents this document. Use this JSON Schema: " +
                        json.dumps(schema)},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500,
    )

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response content: {response.choices[0].message.content}")
        raise

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

        schema = load_json_schema('schedule_schema.json')
        try:
            schedule = get_gpt_response(filepath, schema)
        except json.JSONDecodeError:
            return 'Invalid JSON response from GPT API', 500

        schedule['studentName'] = request.form['name']
        schedule['grade'] = request.form['grade']

        formatted_schedule = json.dumps(schedule)

        return render_template('verify.html', schedule=schedule, formatted_schedule=formatted_schedule)

    return 'File not allowed', 400

@app.route('/confirm', methods=['POST'])
def confirm():
    name = request.form['name']
    grade = request.form['grade']
    schedule = json.loads(request.form['formatted_schedule'])

    new_schedule = Schedule(name=name, grade=grade, schedule=json.dumps(schedule))
    db.session.add(new_schedule)
    db.session.commit()

    return redirect(url_for('schedules'))

@app.route('/schedules')
def schedules():
    all_schedules = Schedule.query.all()
    schedules_list = [
        {
            "name": schedule.name,
            "grade": schedule.grade,
            "schedule": json.loads(schedule.schedule)
        }
        for schedule in all_schedules
    ]
    print(schedules_list)  # Debugging line
    return render_template('schedules.html', schedules=schedules_list)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)
