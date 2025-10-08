from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'secret123'

# مسیر ذخیره فایل‌ها
UPLOAD_FOLDER = 'static/reports'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ساخت دیتابیس در صورت عدم وجود
def init_db():
    conn = sqlite3.connect('inventory.db')
    cur = conn.cursor()
    cur.execute('''
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
    ''')
    conn.commit()
    conn.close()

init_db()

# صفحه اصلی
@app.route('/')
def index():
    conn = sqlite3.connect('inventory.db')
    cur = conn.cursor()

    tool_type = request.args.get('tool_type', '')
    serial_number = request.args.get('serial_number', '')
    size = request.args.get('size', '')

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

    cur.execute(query, params)
    items = cur.fetchall()
    conn.close()

    return render_template('index.html', items=items,
                           tool_type=tool_type,
                           serial_number=serial_number,
                           size=size)

# افزودن ابزار جدید
@app.route('/add', methods=['POST'])
def add():
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']

    report_file = request.files['report_file']
    report_link = ""
    if report_file and report_file.filename:
        path = os.path.join(UPLOAD_FOLDER, report_file.filename)
        report_file.save(path)
        report_link = path

    conn = sqlite3.connect('inventory.db')
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tool_type, serial_number, size, thread_type, location, status, report_link))
    conn.commit()
    conn.close()

    flash('✅ ابزار جدید با موفقیت ثبت شد!')
    return redirect('/')

# بارگذاری و وارد کردن فایل Excel
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    file = request.files['excel_file']
    if not file or not file.filename.endswith('.xlsx'):
        flash('⚠️ لطفاً یک فایل Excel معتبر انتخاب کنید.')
        return redirect('/')

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    df = pd.read_excel(filepath)
    expected_cols = ['id', 'tool_type', 'serial_number', 'size', 'thread_type', 'location', 'status', 'report_link']
    if list(df.columns) != expected_cols:
        flash('❌ ستون‌های فایل Excel با ساختار دیتابیس مطابقت ندارند!')
        return redirect('/')

    conn = sqlite3.connect('inventory.db')
    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO inventory_data (id, tool_type, serial_number, size, thread_type, location, status, report_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(row))
    conn.commit()
    conn.close()

    flash('✅ داده‌های فایل Excel با موفقیت وارد دیتابیس شدند!')
    return redirect('/')

# حذف ابزار
@app.route('/delete/<int:item_id>')
def delete(item_id):
    conn = sqlite3.connect('inventory.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory_data WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash('🗑 ابزار حذف شد.')
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
