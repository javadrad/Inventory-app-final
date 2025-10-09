from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
import openpyxl

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE = os.path.join(DATA_DIR, "inventory.db")
REPORTS_DIR = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
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

def get_db_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET"])
def index():
    tool_type = request.args.get("tool_type", "").strip()
    serial_number = request.args.get("serial_number", "").strip()
    size = request.args.get("size", "").strip()
    location = request.args.get("location", "").strip()
    status = request.args.get("status", "").strip()

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
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if status:
        query += " AND status LIKE ?"
        params.append(f"%{status}%")

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    items = cur.fetchall()
    conn.close()
    return render_template("index.html", items=items, tool_type=tool_type,
                           serial_number=serial_number, size=size, location=location, status=status)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form.get("tool_type", "").strip()
    serial_number = request.form.get("serial_number", "").strip()
    size = request.form.get("size", "").strip()
    thread_type = request.form.get("thread_type", "").strip()
    location = request.form.get("location", "").strip()
    status = request.form.get("status", "").strip()

    report_file = request.files.get("report_file")
    report_link = ""

    if not tool_type:
        flash("نوع ابزار خالی است.", "danger")
        return redirect(url_for("index"))

    conn = get_db_conn()
    c = conn.cursor()
    if serial_number:
        c.execute("SELECT COUNT(*) FROM inventory WHERE serial_number = ?", (serial_number,))
        if c.fetchone()[0] > 0:
            conn.close()
            flash("❌ شماره سریال تکراری است! لطفاً مقدار دیگری وارد کنید.", "danger")
            return redirect(url_for("index"))

    if report_file and report_file.filename:
        filename = secure_filename(report_file.filename)
        save_path = os.path.join(REPORTS_DIR, filename)
        report_file.save(save_path)
        report_link = f"/static/reports/{filename}"

    c.execute("""
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link))
    conn.commit()
    conn.close()

    flash("✅ ابزار با موفقیت ثبت شد.", "success")
    return redirect(url_for("index"))

@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    conn = get_db_conn()
    c = conn.cursor()
    if request.method == "POST":
        tool_type = request.form.get("tool_type", "").strip()
        serial_number = request.form.get("serial_number", "").strip()
        size = request.form.get("size", "").strip()
        thread_type = request.form.get("thread_type", "").strip()
        location = request.form.get("location", "").strip()
        status = request.form.get("status", "").strip()
        report_link = request.form.get("report_link", "")

        report_file = request.files.get("report_file")
        if serial_number:
            c.execute("SELECT COUNT(*) FROM inventory WHERE serial_number = ? AND id != ?", (serial_number, item_id))
            if c.fetchone()[0] > 0:
                conn.close()
                flash("❌ شماره سریال تکراری است! لطفاً مقدار دیگری وارد کنید.", "danger")
                return redirect(url_for("index"))

        if report_file and report_file.filename:
            filename = secure_filename(report_file.filename)
            save_path = os.path.join(REPORTS_DIR, filename)
            report_file.save(save_path)
            report_link = f"/static/reports/{filename}"

        c.execute("""
            UPDATE inventory SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
            WHERE id=?
        """, (tool_type, serial_number, size, thread_type, location, status, report_link, item_id))
        conn.commit()
        conn.close()
        flash("✅ تغییرات با موفقیت ذخیره شد.", "success")
        return redirect(url_for("index"))

    c.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
    item = c.fetchone()
    conn.close()
    return render_template("edit.html", item=item)

@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("🗑️ رکورد حذف شد.", "info")
    return redirect(url_for("index"))

@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or not file.filename:
        flash("فایل اکسل انتخاب نشده است.", "danger")
        return redirect(url_for("index"))

    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        flash("لطفاً فایل اکسل (.xlsx یا .xls) آپلود کنید.", "danger")
        return redirect(url_for("index"))

    tmp_path = os.path.join(BASE_DIR, secure_filename(file.filename))
    file.save(tmp_path)

    try:
        wb = openpyxl.load_workbook(tmp_path)
        sheet = wb.active
    except Exception as e:
        os.remove(tmp_path)
        flash(f"خطا در خواندن فایل اکسل: {e}", "danger")
        return redirect(url_for("index"))

    conn = get_db_conn()
    c = conn.cursor()
    added = 0
    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all([v is None for v in row]):
            continue
        vals = list(row)
        while len(vals) < 7:
            vals.append("")
        tool_type, serial_number, size, thread_type, location, status, report_link = vals[:7]
        try:
            if serial_number:
                c.execute("SELECT COUNT(*) FROM inventory WHERE serial_number = ?", (serial_number,))
                if c.fetchone()[0] > 0:
                    continue
            c.execute("""
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tool_type or "", serial_number or "", size or "", thread_type or "", location or "", status or "", report_link or ""))
            added += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    os.remove(tmp_path)
    flash(f"✅ {added} ردیف از فایل اکسل وارد شد.", "success")
    return redirect(url_for("index"))

@app.route("/static/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORTS_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
