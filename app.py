from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
UPLOAD_FOLDER = 'static/reports'
EXCEL_FOLDER = 'static/excel'
DATABASE = 'inventory.db'
ALLOWED_EXTENSIONS = {'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXCEL_FOLDER'] = EXCEL_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(EXCEL_FOLDER):
    os.makedirs(EXCEL_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_type TEXT,
            serial_number TEXT,
            size TEXT,
            thread_type TEXT,
            location TEXT,
            status TEXT,
            report_link TEXT,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET"])
def index():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    status = request.args.get("status", "")
    location = request.args.get("location", "")

    query = "SELECT * FROM inventory WHERE 1=1"
    params = []

    if tool_type:
        query += " AND tool_type LIKE ?"
        params.append(f"%{tool_type}%")
    if serial_number:
        query += " AND serial_number LIKE ?"
        params.append(f"%{serial_number}%")
    if status:
        query += " AND status = ?"
        params.append(status)
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()

    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, status=status, location=location)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form.get("size", "")
    thread_type = request.form.get("thread_type", "")
    location = request.form.get("location", "")
    status = request.form.get("status", "")
    report_file = request.files.get("report_file")
    description = request.form.get("description", "")

    report_link = ""
    if report_file and report_file.filename != "":
        filename = secure_filename(report_file.filename)
        report_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        report_file.save(report_path)
        report_link = report_path

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form.get("size", "")
        thread_type = request.form.get("thread_type", "")
        location = request.form.get("location", "")
        status = request.form.get("status", "")
        description = request.form.get("description", "")

        report_file = request.files.get("report_file")
        report_link = request.form.get("report_link", "")

        if report_file and report_file.filename != "":
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            report_file.save(report_path)
            report_link = report_path

        cursor.execute('''
            UPDATE inventory SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
            WHERE id=?
        ''', (tool_type, serial_number, size, thread_type, location, status, report_link, description, id))
        conn.commit()
        conn.close()
        return redirect("/")
    else:
        cursor.execute("SELECT * FROM inventory WHERE id=?", (id,))
        item = cursor.fetchone()
        conn.close()
        return render_template("edit.html", item=item)

@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    excel_file = request.files.get("excel_file")
    if excel_file and allowed_file(excel_file.filename):
        filename = secure_filename(excel_file.filename)
        excel_path = os.path.join(app.config['EXCEL_FOLDER'], filename)
        excel_file.save(excel_path)

        df = pd.read_excel(excel_path)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row[0], row[1], row[2], row[3], row[4], row[5], row[6] if len(row) > 6 else ""))
        conn.commit()
        conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
