import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from openpyxl import load_workbook

app = Flask(__name__)
app.secret_key = "inventory_secret_key"

# مسیر ذخیره دیتابیس
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "inventory.db")

# مسیر ذخیره گزارش‌ها
REPORT_DIR = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# تابع ایجاد دیتابیس (در صورت نبود)
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
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

# صفحه اصلی با جستجو
@app.route("/", methods=["GET"])
def index():
    q = request.args.get("q", "").strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if q:
        c.execute("""
            SELECT * FROM inventory_data
            WHERE tool_type LIKE ? OR serial_number LIKE ? OR location LIKE ? OR status LIKE ?
            ORDER BY id DESC
        """, (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        c.execute("SELECT * FROM inventory_data ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return render_template("index.html", data=data)

# افزودن ابزار جدید
@app.route("/add", methods=["POST"])
def add_item():
    tool_type = request.form.get("tool_type") or request.form.get("tool_type_select")
    serial_number = request.form.get("serial_number")
    size = request.form.get("size")
    thread_type = request.form.get("thread_type")
    location = request.form.get("location")
    status = request.form.get("status")
    description = request.form.get("description", "")

    report_file = request.files.get("report_file")
    report_link = None
    if report_file and report_file.filename:
        filename = secure_filename(report_file.filename)
        filepath = os.path.join(REPORT_DIR, filename)
        report_file.save(filepath)
        report_link = f"/static/reports/{filename}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    flash("✅ ابزار با موفقیت ثبت شد.")
    return redirect(url_for("index"))

# ویرایش
@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == "POST":
        tool_type = request.form.get("tool_type")
        serial_number = request.form.get("serial_number")
        size = request.form.get("size")
        thread_type = request.form.get("thread_type")
        location = request.form.get("location")
        status = request.form.get("status")
        description = request.form.get("description", "")

        report_file = request.files.get("report_file")
        report_link = None
        if report_file and report_file.filename:
            filename = secure_filename(report_file.filename)
            filepath = os.path.join(REPORT_DIR, filename)
            report_file.save(filepath)
            report_link = f"/static/reports/{filename}"

        if report_link:
            c.execute("""
                UPDATE inventory_data
                SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
                WHERE id=?
            """, (tool_type, serial_number, size, thread_type, location, status, report_link, description, item_id))
        else:
            c.execute("""
                UPDATE inventory_data
                SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, description=?
                WHERE id=?
            """, (tool_type, serial_number, size, thread_type, location, status, description, item_id))
        conn.commit()
        conn.close()
        flash("✏️ ویرایش با موفقیت انجام شد.")
        return redirect(url_for("index"))

    c.execute("SELECT * FROM inventory_data WHERE id=?", (item_id,))
    item = c.fetchone()
    conn.close()
    return render_template("edit.html", item=item)

# حذف
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM inventory_data WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("🗑 مورد با موفقیت حذف شد.")
    return redirect(url_for("index"))

# آپلود فایل اکسل
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or not file.filename.endswith((".xls", ".xlsx")):
        flash("❌ لطفاً یک فایل اکسل معتبر انتخاب کنید.")
        return redirect(url_for("index"))

    try:
        wb = load_workbook(file)
        ws = wb.active

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row):
                continue

            if len(row) < 7:
                flash(f"⚠️ خطا در سطر {i}: تعداد ستون‌ها باید حداقل 7 باشد.")
                continue

            tool_type, serial_number, size, thread_type, location, status, description = row[:7]

            c.execute("""
                INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(tool_type), str(serial_number), str(size), str(thread_type), str(location), str(status), str(description)))

        conn.commit()
        conn.close()
        flash("✅ داده‌های فایل اکسل با موفقیت بارگذاری شدند.")
    except Exception as e:
        flash(f"❌ خطا در خواندن فایل: {str(e)}")

    return redirect(url_for("index"))

# اجرای برنامه
if __name__ == "__main__":
    app.run(debug=True)
