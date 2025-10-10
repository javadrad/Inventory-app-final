from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join("static", "reports")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_PATH = "inventory.db"

# --- ایجاد دیتابیس اگر وجود نداشته باشد ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_data (
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
    """)
    conn.commit()
    conn.close()

init_db()

# --- صفحه اصلی ---
@app.route("/", methods=["GET"])
def index():
    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")
    status = request.args.get("status", "")
    location = request.args.get("location", "")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT * FROM inventory_data WHERE 1=1"
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
    if status:
        query += " AND status LIKE ?"
        params.append(f"%{status}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()
    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, size=size, status=status, location=location)

# --- افزودن ابزار جدید ---
@app.route("/add", methods=["POST"])
def add_tool():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form.get("size", "")
    thread_type = request.form.get("thread_type", "")
    location = request.form.get("location", "")
    status = request.form.get("status", "")
    report_file = request.files.get("report_file")
    report_link = ""

    if report_file and report_file.filename != "":
        filename = secure_filename(report_file.filename)
        report_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        report_file.save(report_path)
        report_link = "/" + report_path.replace("\\", "/")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link, ""))
    conn.commit()
    conn.close()
    return redirect("/")

# --- ویرایش ابزار ---
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_tool(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form.get("size", "")
        thread_type = request.form.get("thread_type", "")
        location = request.form.get("location", "")
        status = request.form.get("status", "")
        description = request.form.get("description", "")
        report_link = request.form.get("report_link", "")

        report_file = request.files.get("report_file")
        if report_file and report_file.filename != "":
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            report_file.save(report_path)
            report_link = "/" + report_path.replace("\\", "/")

        cursor.execute("""
            UPDATE inventory_data
            SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
            WHERE id=?
        """, (tool_type, serial_number, size, thread_type, location, status, report_link, description, id))
        conn.commit()
        conn.close()
        return redirect("/")
    else:
        cursor.execute("SELECT * FROM inventory_data WHERE id=?", (id,))
        item = cursor.fetchone()
        conn.close()
        return render_template("edit.html", item=item)

# --- حذف ابزار ---
@app.route("/delete/<int:id>")
def delete_tool(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory_data WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# --- آپلود اکسل ---
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    excel_file = request.files.get("excel_file")
    if not excel_file or excel_file.filename == "":
        return "لطفاً یک فایل اکسل انتخاب کنید", 400

    filename = secure_filename(excel_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    excel_file.save(file_path)

    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        elif filename.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            return "فرمت فایل پشتیبانی نمی‌شود", 400
    except Exception as e:
        return f"خطا در خواندن فایل اکسل: {str(e)}", 400

    required_columns = ["tool_type", "serial_number", "size", "thread_type", "location", "status"]
    if not all(col in df.columns for col in required_columns):
        return "ستون‌های فایل اکسل باید شامل tool_type, serial_number, size, thread_type, location, status باشند", 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(row["tool_type"]), str(row["serial_number"]), str(row.get("size", "")), str(row.get("thread_type", "")),
              str(row.get("location", "")), str(row.get("status", "")), "", ""))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
