from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
import sqlite3
from werkzeug.utils import secure_filename

# مسیرهای اصلی پروژه
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "inventory.db")

# ایجاد پوشه‌های لازم (در صورت نبود)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "reports"), exist_ok=True)

app = Flask(__name__)
app.secret_key = 'my_secret_key'
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "reports")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🗄️ ایجاد جدول دیتابیس (در صورت عدم وجود)
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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
init_db()

# 📥 صفحه اصلی
@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM inventory_data")
    data = cur.fetchall()
    conn.close()
    return render_template('index.html', data=data)

# 📤 آپلود فایل اکسل
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    file = request.files['excel_file']
    if not file:
        flash('هیچ فایلی انتخاب نشده است.')
        return redirect(url_for('index'))
    filename = secure_filename(file.filename)
    path = os.path.join(BASE_DIR, filename)
    file.save(path)
    flash('فایل با موفقیت آپلود شد.')
    return redirect(url_for('index'))

# ➕ افزودن رکورد جدید
@app.route('/add', methods=['POST'])
def add_record():
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']
    report_link = request.files.get('report_link')

    report_path = ""
    if report_link and report_link.filename:
        filename = secure_filename(report_link.filename)
        report_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        report_link.save(report_path)
        report_path = f"reports/{filename}"

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tool_type, serial_number, size, thread_type, location, status, report_path))
        conn.commit()

    flash('رکورد با موفقیت اضافه شد.')
    return redirect(url_for('index'))

# ✏️ ویرایش رکورد
@app.route('/edit/<int:record_id>', methods=['POST'])
def edit_record(record_id):
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']
    report_link = request.files.get('report_link')

    with sqlite3.connect(DB_PATH) as conn:
        if report_link and report_link.filename:
            filename = secure_filename(report_link.filename)
            report_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            report_link.save(report_path)
            report_path = f"reports/{filename}"
            conn.execute("""
                UPDATE inventory_data
                SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
                WHERE id=?
            """, (tool_type, serial_number, size, thread_type, location, status, report_path, record_id))
        else:
            conn.execute("""
                UPDATE inventory_data
                SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?
                WHERE id=?
            """, (tool_type, serial_number, size, thread_type, location, status, record_id))
        conn.commit()

    flash('اطلاعات با موفقیت ویرایش شد.')
    return redirect(url_for('index'))

# 🗑️ حذف رکورد
@app.route('/delete/<int:record_id>')
def delete_record(record_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM inventory_data WHERE id=?", (record_id,))
        conn.commit()
    flash('رکورد حذف شد.')
    return redirect(url_for('index'))

# 📄 دسترسی به فایل گزارش
@app.route('/reports/<path:filename>')
def serve_report(filename):
    return send_from_directory(os.path.join('static', 'reports'), filename)

if __name__ == '__main__':
    app.run(debug=True)
