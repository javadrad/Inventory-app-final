from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secure-key-1234"

# مسیر اصلی پروژه
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")
REPORTS_FOLDER = os.path.join(BASE_DIR, "static", "reports")

os.makedirs(REPORTS_FOLDER, exist_ok=True)


# ----------------- ایجاد دیتابیس -----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_type TEXT,
            serial_number TEXT UNIQUE,
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


# ----------------- صفحه اصلی با جستجو -----------------
@app.route("/", methods=["GET"])
def index():
    tool_type = request.args.get("tool_type", "").strip()
    serial_number = request.args.get("serial_number", "").strip()
    status = request.args.get("status", "").strip()
    location = request.args.get("location", "").strip()

    query = "SELECT * FROM inventory_data WHERE 1=1"
    params = []

    if tool_type:
        query += " AND tool_type LIKE ?"
        params.append(f"%{tool_type}%")
    if serial_number:
        query += " AND serial_number LIKE ?"
        params.append(f"%{serial_number}%")
    if status:
        query += " AND status LIKE ?"
        params.append(f"%{status}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.close()

    return render_template("index.html", data=data, tool_type=tool_type,
                           serial_number=serial_number, status=status, location=location)


# ----------------- افزودن ابزار جدید -----------------
@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]
    report_file = request.files["report_link"]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # بررسی شماره سریال تکراری
    c.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number = ?", (serial_number,))
    if c.fetchone()[0] > 0:
        conn.close()
        flash("❌ شماره سریال تکراری است! لطفاً مقدار دیگری وارد کنید.")
        return redirect(url_for("index"))

    report_path = None
    if report_file and report_file.filename:
        filename = secure_filename(report_file.filename)
        report_path = os.path.join(REPORTS_FOLDER, filename)
        report_file.save(report_path)

    c.execute("""
        INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_path))

    conn.commit()
    conn.close()
    flash("✅ رکورد با موفقیت اضافه شد.")
    return redirect(url_for("index"))


# ----------------- ویرایش رکورد -----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form["size"]
        thread_type = request.form["thread_type"]
        location = request.form["location"]
        status = request.form["status"]
        report_file = request.files["report_file"]
        report_link = request.form["report_link"]

        # بررسی شماره سریال تکراری (به جز رکورد جاری)
        c.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number = ? AND id != ?", (serial_number, id))
        if c.fetchone()[0] > 0:
            conn.close()
            flash("❌ شماره سریال تکراری است! لطفاً مقدار دیگری وارد کنید.")
            return redirect(url_for("index"))

        if report_file and report_file.filename:
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(REPORTS_FOLDER, filename)
            report_file.save(report_path)
        else:
            report_path = report_link

        c.execute("""
            UPDATE inventory_data
            SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
            WHERE id=?
        """, (tool_type, serial_number, size, thread_type, location, status, report_path, id))

        conn.commit()
        conn.close()
        flash("✅ تغییرات با موفقیت ثبت شد.")
        return redirect(url_for("index"))

    else:
        c.execute("SELECT * FROM inventory_data WHERE id=?", (id,))
        item = c.fetchone()
        conn.close()
        return render_template("edit.html", item=item)


# ----------------- حذف رکورد -----------------
@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM inventory_data WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("🗑️ رکورد حذف شد.")
    return redirect(url_for("index"))


# ----------------- ارائه فایل‌های گزارش -----------------
@app.route("/reports/<path:filename>")
def reports(filename):
    return send_from_directory(REPORTS_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)
