from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
import openpyxl

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join("static", "reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DATABASE = "inventory.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_type TEXT,
            serial_number TEXT,
            size TEXT,
            thread_type TEXT,
            location TEXT,
            status TEXT,
            report_link TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory")
    items = cursor.fetchall()
    conn.close()
    return render_template("index.html", items=items)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]

    report_file = request.files.get("report_file")
    report_link = ""
    if report_file and report_file.filename.endswith(".pdf"):
        filename = secure_filename(report_file.filename)
        report_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        report_file.save(report_path)
        report_link = f"/static/reports/{filename}"

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or not file.filename.endswith(".xlsx"):
        return redirect(url_for("index"))

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
    file.save(filepath)

    wb = openpyxl.load_workbook(filepath)
    sheet = wb.active

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row and len(row) >= 7:
            cursor.execute("""
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, row)

    conn.commit()
    conn.close()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
