from flask import Flask, request, render_template, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os
import base64
import json
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import time

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
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

def get_gpt_response(image_path, schema, retries=3):
    with open(image_path, 'rb') as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    for attempt in range(retries):
        try:
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

            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2)  # wait before retrying
            else:
                raise
    raise Exception("Maximum retry attempts reached")

# Define a list of pastel colors following the rainbow pattern
PASTEL_COLORS = [
    "#FFB3BA",  # light red
    "#FFDFBA",  # light orange
    "#FFFFBA",  # light yellow
    "#BAFFC9",  # light green
    "#BAE1FF",  # light blue
    "#E3BAFF",  # light purple
]

def generate_color(index):
    return PASTEL_COLORS[index % len(PASTEL_COLORS)]

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
        for attempt in range(3):
            try:
                schedule = get_gpt_response(filepath, schema)
                break
            except Exception as e:
                if attempt < 2:
                    print(f"GPT API call failed, retrying... (Attempt {attempt + 1})")
                else:
                    return 'Failed to process the image. Please ensure it is a correct schedule image and try again.', 500

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

    # Create a dictionary to track shared classes
    shared_classes = {}
    index_counter = 0
    
    for schedule in all_schedules:
        schedule_data = json.loads(schedule.schedule)
        for period, entry in schedule_data['semester1'].items():
            key = f"{entry['class']}_{period}"
            if key not in shared_classes:
                shared_classes[key] = generate_color(index_counter)
                index_counter += 1

        for period, entry in schedule_data['semester2'].items():
            key = f"{entry['class']}_{period}"
            if key not in shared_classes:
                shared_classes[key] = generate_color(index_counter)
                index_counter += 1

    schedules_list = [
        {
            "name": schedule.name,
            "grade": schedule.grade,
            "schedule": json.loads(schedule.schedule),
            "colors": shared_classes
        }
        for schedule in all_schedules
    ]

    return render_template('schedules.html', schedules=schedules_list)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)
