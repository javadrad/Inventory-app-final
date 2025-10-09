from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import sqlite3, os, shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'tool_management_secret'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "inventory.db")
REPORT_FOLDER = os.path.join("static", "reports")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# ======== اتصال و ساخت جدول ========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS inventory_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_type TEXT,
        serial_number TEXT,
        size TEXT,
        thread_type TEXT,
        location TEXT,
        status TEXT,
        report_link TEXT,
        notes TEXT DEFAULT ''
    )''')
    conn.commit()
    conn.close()

init_db()

# ======== صفحه اصلی ========
@app.route('/')
def index():
    tool_type = request.args.get('tool_type', '')
    serial_number = request.args.get('serial_number', '')
    size = request.args.get('size', '')
    location = request.args.get('location', '')
    status = request.args.get('status', '')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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

    cur.execute(query, params)
    items = cur.fetchall()
    conn.close()

    return render_template("index.html", items=items)

# ======== افزودن ابزار ========
@app.route('/add', methods=['POST'])
def add_item():
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']
    notes = request.form.get('notes', '')

    report_file = request.files.get('report_file')
    report_link = None
    if report_file and report_file.filename:
        filename = secure_filename(report_file.filename)
        save_path = os.path.join(REPORT_FOLDER, filename)
        report_file.save(save_path)
        report_link = f"/{REPORT_FOLDER}/{filename}"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (tool_type, serial_number, size, thread_type, location, status, report_link, notes))
    conn.commit()
    conn.close()

    flash("✅ ابزار جدید با موفقیت ثبت شد.", "success")
    return redirect(url_for('index'))

# ======== حذف ابزار ========
@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory_data WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("🗑 ابزار حذف شد.", "warning")
    return redirect(url_for('index'))

# ======== ویرایش ابزار ========
@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == 'POST':
        tool_type = request.form['tool_type']
        serial_number = request.form['serial_number']
        size = request.form['size']
        thread_type = request.form['thread_type']
        location = request.form['location']
        status = request.form['status']
        notes = request.form.get('notes', '')

        report_file = request.files.get('report_file')
        if report_file and report_file.filename:
            filename = secure_filename(report_file.filename)
            save_path = os.path.join(REPORT_FOLDER, filename)
            report_file.save(save_path)
            report_link = f"/{REPORT_FOLDER}/{filename}"
            cur.execute('''UPDATE inventory_data SET tool_type=?, serial_number=?, size=?, thread_type=?, 
                        location=?, status=?, report_link=?, notes=? WHERE id=?''',
                        (tool_type, serial_number, size, thread_type, location, status, report_link, notes, item_id))
        else:
            cur.execute('''UPDATE inventory_data SET tool_type=?, serial_number=?, size=?, thread_type=?, 
                        location=?, status=?, notes=? WHERE id=?''',
                        (tool_type, serial_number, size, thread_type, location, status, notes, item_id))

        conn.commit()
        conn.close()
        flash("✏️ اطلاعات ابزار با موفقیت ویرایش شد.", "info")
        return redirect(url_for('index'))

    cur.execute("SELECT * FROM inventory_data WHERE id=?", (item_id,))
    item = cur.fetchone()
    conn.close()
    return render_template("edit.html", item=item)

# ======== آپلود فایل اکسل ========
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    import openpyxl

    excel_file = request.files.get('excel_file')
    if not excel_file:
        flash("لطفاً فایل اکسل انتخاب شود.", "danger")
        return redirect(url_for('index'))

    try:
        wb = openpyxl.load_workbook(excel_file)
        ws = wb.active
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        for row in ws.iter_rows(min_row=2, values_only=True):
            if len(row) < 6:
                continue
            tool_type, serial_number, size, thread_type, location, status = row[:6]
            report_link = row[6] if len(row) > 6 else None
            notes = row[7] if len(row) > 7 else ''
            cur.execute('''INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, notes)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (tool_type, serial_number, size, thread_type, location, status, report_link, notes))
        conn.commit()
        conn.close()
        flash("📥 داده‌های اکسل با موفقیت وارد شدند.", "success")
    except Exception as e:
        flash(f"❌ خطا در بارگذاری فایل اکسل: {e}", "danger")

    return redirect(url_for('index'))

# ======== ارائه فایل‌ها ========
@app.route('/static/reports/<path:filename>')
def serve_report(filename):
    return send_from_directory(REPORT_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
