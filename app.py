from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

DB_NAME = "tools_data.db"

# ایجاد دیتابیس در صورت نبود
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_type TEXT,
                serial_number TEXT,
                size TEXT,
                thread_type TEXT,
                location TEXT,
                status TEXT,
                report_link TEXT,
                description TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory_data")
    data = c.fetchall()
    conn.close()
    return render_template('index.html', data=data)

# افزودن ابزار به صورت دستی
@app.route('/add', methods=['POST'])
def add_tool():
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']
    report_link = request.form['report_link']
    description = request.form['description']

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# آپلود فایل اکسل
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    file = request.files['file']
    if file and file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file)
        conn = sqlite3.connect(DB_NAME)
        df.to_sql('inventory_data', conn, if_exists='append', index=False)
        conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_tool(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if request.method == 'POST':
        c.execute('''UPDATE inventory_data SET
                     tool_type=?, serial_number=?, size=?, thread_type=?, location=?,
                     status=?, report_link=?, description=? WHERE id=?''',
                  (request.form['tool_type'], request.form['serial_number'], request.form['size'],
                   request.form['thread_type'], request.form['location'], request.form['status'],
                   request.form['report_link'], request.form['description'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        c.execute("SELECT * FROM inventory_data WHERE id=?", (id,))
        data = c.fetchone()
        conn.close()
        return render_template('edit.html', data=data)

@app.route('/delete/<int:id>')
def delete_tool(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM inventory_data WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
