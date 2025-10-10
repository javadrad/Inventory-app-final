from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "reports")
EXCEL_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXCEL_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["EXCEL_FOLDER"] = EXCEL_FOLDER

DATABASE = os.path.join(BASE_DIR, "inventory.db")

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
            report_link TEXT,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST" and "excel_file" in request.files:
        excel_file = request.files["excel_file"]
        if excel_file.filename == "":
            flash("لطفاً یک فایل اکسل انتخاب کنید.")
            return redirect(url_for("index"))
        filename = secure_filename(excel_file.filename)
        filepath = os.path.join(app.config["EXCEL_FOLDER"], filename)
        excel_file.save(filepath)
        try:
            df = pd.read_excel(filepath)
            expected_columns = ["tool_type", "serial_number", "size", "thread_type", "location", "status", "description"]
            if list(df.columns) != expected_columns:
                flash(f"ستون‌های فایل اکسل باید به ترتیب: {expected_columns} باشند.")
                return redirect(url_for("index"))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                               (row["tool_type"], row["serial_number"], row["size"], row["thread_type"], row["location"], row["status"], row["description"]))
            conn.commit()
            flash("بارگذاری و وارد کردن داده‌ها موفقیت‌آمیز بود.", "success")
        except Exception as e:
            flash(f"خطا در بارگذاری فایل اکسل: {e}", "danger")
        return redirect(url_for("index"))

    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")
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
    if size:
        query += " AND size LIKE ?"
        params.append(f"%{size}%")
    if status:
        query += " AND status=?"
        params.append(status)
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()
    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, size=size, status=status, location=location)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]
    description = request.form.get("description", "")

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
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    flash("ابزار با موفقیت ثبت شد.", "success")
    return redirect(url_for("index"))

@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form["size"]
        thread_type = request.form["thread_type"]
        location = request.form["location"]
        status = request.form["status"]
        description = request.form.get("description", "")

        report_file = request.files.get("report_file")
        report_link = request.form.get("report_link", "")

        if report_file and report_file.filename.endswith(".pdf"):
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            report_file.save(report_path)
            report_link = f"/static/reports/{filename}"

        cursor.execute("""
            UPDATE inventory SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
            WHERE id=?""",
                       (tool_type, serial_number, size, thread_type, location, status, report_link, description, item_id))
        conn.commit()
        conn.close()
        flash("ابزار با موفقیت ویرایش شد.", "success")
        return redirect(url_for("index"))

    cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    return render_template("edit.html", item=item)

@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("ابزار حذف شد.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
