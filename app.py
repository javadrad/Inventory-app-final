from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import openpyxl
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret_key"

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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        excel_file = request.files.get("excel_file")
        if excel_file and excel_file.filename.endswith((".xlsx", ".xls")):
            try:
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                for i, row in enumerate(sheet.iter_rows(values_only=True)):
                    if i == 0:
                        continue  # رد کردن سطر هدر
                    cursor.execute("""
                        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                   (row[1], row[2], row[3], row[4], row[5], row[6], row[7]))
                conn.commit()
                conn.close()
                flash("بارگذاری Excel با موفقیت انجام شد.", "success")
            except Exception as e:
                flash(f"خطا در بارگذاری Excel: {e}", "error")
        else:
            flash("لطفاً یک فایل Excel معتبر انتخاب کنید.", "error")
        return redirect(url_for("index"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")

    query = "SELECT * FROM inventory WHERE 1=1"
    params = []
    if tool_type:
        query += " AND tool_type LIKE ?"
        params.append(f"%{tool_type}%")
    if serial_number:
        query += " AND serial_number LIKE ?"
        params.append(f"%{serial_number}%")
    if size:
        query += " AND size LIKE ?"
        params.append(f"%{size}%")

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()

    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, size=size)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]

    report_file = request.files.get("report_file")
