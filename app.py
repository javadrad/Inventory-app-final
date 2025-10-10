from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
app.secret_key = "replace_with_a_real_secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")
REPORT_DIR = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

ALLOWED_REPORT_EXT = {".pdf"}
ALLOWED_EXCEL_EXT = {".xlsx", ".xls"}

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
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

# Helper: connect
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Index + search (GET). Upload Excel handled by separate POST route below.
@app.route("/", methods=["GET"])
def index():
    # search filters
    tool_type = request.args.get("tool_type", "").strip()
    serial_number = request.args.get("serial_number", "").strip()
    size = request.args.get("size", "").strip()
    status = request.args.get("status", "").strip()
    location = request.args.get("location", "").strip()

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
        query += " AND status = ?"
        params.append(status)
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

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
                           status=status,
                           location=location)

# Add new tool
@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form.get("tool_type", "").strip()
    serial_number = request.form.get("serial_number", "").strip()
    size = request.form.get("size", "").strip()
    thread_type = request.form.get("thread_type", "").strip()
    location = request.form.get("location", "").strip()
    status = request.form.get("status", "").strip()
    description = request.form.get("description", "").strip()

    report_file = request.files.get("report_file")
    report_link = ""
    if report_file and report_file.filename:
        _, ext = os.path.splitext(report_file.filename.lower())
        if ext in ALLOWED_REPORT_EXT:
            filename = secure_filename(report_file.filename)
            save_path = os.path.join(REPORT_DIR, filename)
            report_file.save(save_path)
            report_link = f"/static/reports/{filename}"
        else:
            flash("فایل گزارش باید PDF باشد.", "danger")
            return redirect(url_for("index"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    flash("✅ ابزار با موفقیت ثبت شد.", "success")
    return redirect(url_for("index"))

# Edit
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

        report_file = request.files.get("report_file")
        report_link = request.form.get("report_link", "").strip() or ""

        if report_file and report_file.filename:
            _, ext = os.path.splitext(report_file.filename.lower())
            if ext in ALLOWED_REPORT_EXT:
                filename = secure_filename(report_file.filename)
                save_path = os.path.join(REPORT_DIR, filename)
                report_file.save(save_path)
                report_link = f"/static/reports/{filename}"
            else:
                flash("فایل گزارش باید PDF باشد.", "danger")
                return redirect(url_for("edit", item_id=item_id))

        cur.execute("""
            UPDATE inventory
            SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
            WHERE id=?
        """, (tool_type, serial_number, size, thread_type, location, status, report_link, description, item_id))
        conn.commit()
        conn.close()
        flash("✏️ ویرایش با موفقیت ذخیره شد.", "success")
        return redirect(url_for("index"))

    cur.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
    item = cur.fetchone()
    conn.close()
    if not item:
        flash("ردیف پیدا نشد.", "danger")
        return redirect(url_for("index"))
    return render_template("edit.html", item=item)

# Delete
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("🗑 رکورد حذف شد.", "info")
    return redirect(url_for("index"))

# Upload Excel (only XLSX/XLS)
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    excel_file = request.files.get("excel_file")
    if not excel_file or not excel_file.filename:
        flash("لطفاً یک فایل اکسل (.xlsx یا .xls) انتخاب کنید.", "danger")
        return redirect(url_for("index"))

    filename = secure_filename(excel_file.filename)
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXCEL_EXT:
        flash("فرمت فایل پشتیبانی نمی‌شود. لطفاً یک فایل .xlsx یا .xls انتخاب کنید.", "danger")
        return redirect(url_for("index"))

    try:
        # pandas can read the file-like object directly
        df = pd.read_excel(excel_file)
    except Exception as e:
        flash(f"خطا در خواندن فایل اکسل: {e}", "danger")
        return redirect(url_for("index"))

    # required columns (description optional)
    required = ["tool_type", "serial_number", "size", "thread_type", "location", "status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        flash(f"ستون‌های فایل اکسل باید شامل: {', '.join(required)} باشند. ستون‌های ناقص: {', '.join(missing)}", "danger")
        return redirect(url_for("index"))

    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("tool_type", "")).strip(),
                str(row.get("serial_number", "")).strip(),
                str(row.get("size", "")).strip(),
                str(row.get("thread_type", "")).strip(),
                str(row.get("location", "")).strip(),
                str(row.get("status", "")).strip(),
                "",  # report_link empty by default; user can upload per-row via edit
                str(row.get("description", "")).strip()
            ))
            inserted += 1
        except Exception:
            # skip problematic rows
            continue
    conn.commit()
    conn.close()
    flash(f"✅ {inserted} ردیف از فایل اکسل وارد شد.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    # debug=False in production — here debug True for easier testing
    app.run(debug=True, host="0.0.0.0", port=5000)
