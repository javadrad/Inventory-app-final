import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import openpyxl

# ------------------ تنظیمات اولیه ------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# مسیر اصلی پروژه
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# مسیر پوشه دیتابیس
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# مسیر فایل دیتابیس
DB_PATH = os.path.join(DATA_DIR, "inventory.db")

# مسیر پوشه ذخیره گزارش‌ها
REPORT_DIR = os.path.join(BASE_DIR, "static", "reports")
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

# مسیر پوشه آپلود اکسل
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"xlsx"}


# ------------------ توابع دیتابیس ------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_data (
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


# ------------------ مسیر اصلی ------------------
@app.route("/", methods=["GET"])
def index():
    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")

    conn = get_db_connection()
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

    items = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, size=size)


# ------------------ افزودن ابزار ------------------
@app.route("/add", methods=["POST"])
def add_tool():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]

    report_file = request.files.get("report_file")
    report_link = ""

    if report_file and report_file.filename:
        filename = secure_filename(report_file.filename)
        save_path = os.path.join(REPORT_DIR, filename)
        report_file.save(save_path)
        report_link = f"/static/reports/{filename}"

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link))
    conn.commit()
    conn.close()

    flash("✅ ابزار جدید با موفقیت اضافه شد", "success")
    return redirect(url_for("index"))


# ------------------ حذف ابزار ------------------
@app.route("/delete/<int:item_id>")
def delete_item(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM inventory_data WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    flash("🗑 ابزار حذف شد", "info")
    return redirect(url_for("index"))


# ------------------ ویرایش ابزار ------------------
@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    conn = get_db_connection()

    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form["size"]
        thread_type = request.form["thread_type"]
        location = request.form["location"]
        status = request.form["status"]

        report_file = request.files.get("report_file")
        report_link = request.form.get("report_link")

        if report_file and report_file.filename:
            filename = secure_filename(report_file.filename)
            save_path = os.path.join(REPORT_DIR, filename)
            report_file.save(save_path)
            report_link = f"/static/reports/{filename}"

        conn.execute("""
            UPDATE inventory_data
            SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
            WHERE id=?
        """, (tool_type, serial_number, size, thread_type, location, status, report_link, item_id))
        conn.commit()
        conn.close()
        flash("✏️ اطلاعات ابزار بروزرسانی شد", "success")
        return redirect(url_for("index"))

    item = conn.execute("SELECT * FROM inventory_data WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return render_template("edit.html", item=item)


# ------------------ آپلود فایل اکسل ------------------
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or not file.filename.endswith(".xlsx"):
        flash("⚠ لطفاً یک فایل Excel معتبر انتخاب کنید.", "danger")
        return redirect(url_for("index"))

    path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
    file.save(path)

    wb = openpyxl.load_workbook(path)
    sheet = wb.active

    conn = get_db_connection()
    added = 0
    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        try:
            if len(row) != 7:
                flash(f"⚠ خطا در سطر {i}: تعداد ستون‌ها باید 7 باشد.", "danger")
                continue
            conn.execute("""
                INSERT INTO inventory_data (id, tool_type, serial_number, size, thread_type, location, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, row)
            added += 1
        except Exception as e:
            flash(f"❌ خطا در سطر {i}: {e}", "danger")
    conn.commit()
    conn.close()

    flash(f"✅ {added} ردیف با موفقیت از فایل Excel افزوده شد.", "success")
    return redirect(url_for("index"))


# ------------------ اجرای برنامه ------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
