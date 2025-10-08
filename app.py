from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from openpyxl import load_workbook

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

@app.route("/", methods=["GET"])
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
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        report_file.save(path)
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
    file = request.files["excel_file"]
    if file and file.filename.endswith((".xlsx", ".xls")):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)

        wb = load_workbook(path)
        ws = wb.active

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        for row in ws.iter_rows(min_row=2, values_only=True):
            cursor.execute("""
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, row)
        conn.commit()
        conn.close()
        wb.close()

        return redirect(url_for("index"))

    return "فایل اکسل معتبر نیست!"

@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
