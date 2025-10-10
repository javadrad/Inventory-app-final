import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from openpyxl import load_workbook

app = Flask(__name__)
app.secret_key = "replace-this-with-a-real-secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# دیتابیس در پوشه data برای پایداری
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "inventory.db")

# مسیر ذخیره گزارش‌ها
REPORT_DIR = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# --- ایجاد جدول (اگر وجود نداشته باشد) ---
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
            report_link TEXT,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# کوچک‌کننده‌ی helper برای اتصال
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- صفحه اصلی و جستجو ----------
@app.route("/", methods=["GET"])
def index():
    tool_type = request.args.get("tool_type", "").strip()
    serial_number = request.args.get("serial_number", "").strip()
    size = request.args.get("size", "").strip()
    location = request.args.get("location", "").strip()
    status = request.args.get("status", "").strip()

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
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if status:
        query += " AND status LIKE ?"
        params.append(f"%{status}%")

    query += " ORDER BY id DESC"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    items = cur.fetchall()
    conn.close()

    return render_template("index.html",
                           items=items,
                           tool_type=tool_type,
                           serial_number=serial_number,
                           size=size,
                           location=location,
                           status=status)

# ---------- افزودن ابزار ----------
@app.route("/add", methods=["POST"])
def add():
    # اولویت: اگر کاربر از select انتخاب کرده باشد، JS مقدار را در input می‌ریزد
    tool_type = request.form.get("tool_type", "").strip()
    serial_number = request.form.get("serial_number", "").strip()
    size = request.form.get("size", "").strip()
    thread_type = request.form.get("thread_type", "").strip()
    location = request.form.get("location", "").strip()
    status = request.form.get("status", "").strip()
    description = request.form.get("description", "").strip()

    # جلوگیری از سریال تکراری (اختیاری اما مفید)
    if serial_number:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number = ?", (serial_number,))
        if cur.fetchone()[0] > 0:
            conn.close()
            flash("❌ شماره سریال تکراری است. ثبت انجام نشد.", "danger")
            return redirect(url_for("index"))
        conn.close()

    report_file = request.files.get("report_file")
    report_link = None
    if report_file and report_file.filename:
        filename = secure_filename(report_file.filename)
        save_path = os.path.join(REPORT_DIR, filename)
        report_file.save(save_path)
        report_link = f"/static/reports/{filename}"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()

    flash("✅ ابزار با موفقیت ثبت شد.", "success")
    return redirect(url_for("index"))

# ---------- ویرایش ----------
@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":
        tool_type = request.form.get("tool_type", "").strip()
        serial_number = request.form.get("serial_number", "").strip()
        size = request.form.get("size", "").strip()
        thread_type = request.form.get("thread_type", "").strip()
        location = request.form.get("location", "").strip()
        status = request.form.get("status", "").strip()
        description = request.form.get("description", "").strip()

        # چک تکراری بودن شماره سریال برای سایر رکوردها
        if serial_number:
            cur.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number = ? AND id != ?", (serial_number, item_id))
            if cur.fetchone()[0] > 0:
                conn.close()
                flash("❌ شماره سریال تکراری است! تغییرات اعمال نشد.", "danger")
                return redirect(url_for("index"))

        report_file = request.files.get("report_file")
        if report_file and report_file.filename:
            filename = secure_filename(report_file.filename)
            save_path = os.path.join(REPORT_DIR, filename)
            report_file.save(save_path)
            report_link = f"/static/reports/{filename}"
            cur.execute("""
                UPDATE inventory_data
                SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
                WHERE id=?
            """, (tool_type, serial_number, size, thread_type, location, status, report_link, description, item_id))
        else:
            cur.execute("""
                UPDATE inventory_data
                SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, description=?
                WHERE id=?
            """, (tool_type, serial_number, size, thread_type, location, status, description, item_id))

        conn.commit()
        conn.close()
        flash("✏️ تغییرات ذخیره شد.", "success")
        return redirect(url_for("index"))

    # GET
    cur.execute("SELECT * FROM inventory_data WHERE id=?", (item_id,))
    item = cur.fetchone()
    conn.close()
    if not item:
        flash("ردیف پیدا نشد.", "danger")
        return redirect(url_for("index"))
    return render_template("edit.html", item=item)

# ---------- حذف (POST) ----------
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory_data WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("🗑 رکورد حذف شد.", "info")
    return redirect(url_for("index"))

# ---------- آپلود اکسل (فرم کاملاً جدا) ----------
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or file.filename == "":
        flash("فایل اکسل انتخاب نشده است.", "danger")
        return redirect(url_for("index"))

    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        flash("لطفا فایل اکسل (.xlsx یا .xls) آپلود کنید.", "danger")
        return redirect(url_for("index"))

    # بارگذاری در حافظه و خواندن با openpyxl
    try:
        wb = load_workbook(file)
        ws = wb.active
    except Exception as e:
        flash(f"خطا در خواندن فایل اکسل: {e}", "danger")
        return redirect(url_for("index"))

    conn = get_conn()
    cur = conn.cursor()
    added = 0
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # انتظار حداقل 6 ستون: tool_type, serial_number, size, thread_type, location, status
        if not row or all(v is None for v in row):
            continue
        vals = list(row)
        # pad to at least 6
        while len(vals) < 6:
            vals.append("")
        # optional description in 7th position
        if len(vals) >= 7:
            description = vals[6] or ""
        else:
            description = ""
        tool_type = str(vals[0] or "")
        serial_number = str(vals[1] or "")
        size = str(vals[2] or "")
        thread_type = str(vals[3] or "")
        location = str(vals[4] or "")
        status = str(vals[5] or "")

        try:
            # prevent duplicate serial_number
            if serial_number:
                cur.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number = ?", (serial_number,))
                if cur.fetchone()[0] > 0:
                    continue
            cur.execute("""
                INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tool_type, serial_number, size, thread_type, location, status, description))
            added += 1
        except Exception:
            # skip bad row
            continue

    conn.commit()
    conn.close()
    flash(f"✅ {added} ردیف از فایل اکسل وارد شد.", "success")
    return redirect(url_for("index"))

# ---------- ارائه فایل گزارش ----------
@app.route("/static/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORT_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)
