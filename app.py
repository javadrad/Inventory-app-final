import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xlsx'}

# اتصال به دیتابیس
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_type TEXT,
        serial_number TEXT,
        size TEXT,
        thread_type TEXT,
        location TEXT,
        status TEXT,
        report_link TEXT,
        description TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    query = request.args.get('query', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if query:
        c.execute("""SELECT * FROM inventory_data WHERE 
                     tool_type LIKE ? OR
                     serial_number LIKE ? OR
                     size LIKE ? OR
                     thread_type LIKE ? OR
                     location LIKE ? OR
                     status LIKE ?""",
                     tuple(f"%{query}%" for _ in range(6)))
    else:
        c.execute("SELECT * FROM inventory_data")
    data = c.fetchall()
    conn.close()
    return render_template('index.html', data=data, query=query)

@app.route('/add', methods=['POST'])
def add():
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']
    report_link = request.form.get('report_link', '')
    description = request.form.get('description', '')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    file = request.files['excel_file']
    if not file or not allowed_file(file.filename):
        return "لطفاً فایل XLSX معتبر انتخاب کنید", 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    df = pd.read_excel(file_path)
    expected_cols = ['tool_type', 'serial_number', 'size', 'thread_type', 'location', 'status']
    if len(df.columns) < len(expected_cols):
        return "ساختار فایل اکسل معتبر نیست", 400

    df.columns = expected_cols[:len(df.columns)]

    conn = sqlite3.connect(DB_PATH)
    df.to_sql('inventory_data', conn, if_exists='append', index=False)
    conn.close()

    return redirect(url_for('index'))

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        c.execute("""UPDATE inventory_data SET
                     tool_type=?, serial_number=?, size=?, thread_type=?, location=?, 
                     status=?, report_link=?, description=? WHERE id=?""",
                  (request.form['tool_type'], request.form['serial_number'], request.form['size'],
                   request.form['thread_type'], request.form['location'], request.form['status'],
                   request.form['report_link'], request.form['description'], item_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    c.execute("SELECT * FROM inventory_data WHERE id=?", (item_id,))
    item = c.fetchone()
    conn.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:item_id>')
def delete(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM inventory_data WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
