from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
import pandas as pd

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------- Database Initialization ----------
def init_db():
    conn = sqlite3.connect('tools.db')
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

# ---------- Routes ----------
@app.route('/')
def index():
    conn = sqlite3.connect('tools.db')
    c = conn.cursor()
    c.execute("SELECT * FROM inventory_data")
    data = c.fetchall()
    conn.close()
    return render_template('index.html', data=data)

@app.route('/add', methods=['POST'])
def add():
    tool_type = request.form['tool_type']
    serial_number = request.form['serial_number']
    size = request.form['size']
    thread_type = request.form['thread_type']
    location = request.form['location']
    status = request.form['status']
    report_file = request.files['report_link']
    description = request.form.get('description', '')

    report_filename = ''
    if report_file and report_file.filename:
        report_filename = os.path.join(app.config['UPLOAD_FOLDER'], report_file.filename)
        report_file.save(report_filename)

    conn = sqlite3.connect('tools.db')
    c = conn.cursor()
    c.execute('''INSERT INTO inventory_data 
                 (tool_type, serial_number, size, thread_type, location, status, report_link, description)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (tool_type, serial_number, size, thread_type, location, status, report_filename, description))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    conn = sqlite3.connect('tools.db')
    c = conn.cursor()

    if request.method == 'POST':
        tool_type = request.form['tool_type']
        serial_number = request.form['serial_number']
        size = request.form['size']
        thread_type = request.form['thread_type']
        location = request.form['location']
        status = request.form['status']
        description = request.form.get('description', '')

        c.execute('''UPDATE inventory_data SET 
                        tool_type=?, serial_number=?, size=?, thread_type=?, 
                        location=?, status=?, description=? 
                     WHERE id=?''',
                  (tool_type, serial_number, size, thread_type, location, status, description, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        c.execute("SELECT * FROM inventory_data WHERE id=?", (id,))
        item = c.fetchone()
        conn.close()
        return render_template('edit.html', item=item)

@app.route('/delete/<int:id>')
def delete(id):
    conn = sqlite3.connect('tools.db')
    c = conn.cursor()
    c.execute("DELETE FROM inventory_data WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    file = request.files['excel_file']
    if file and file.filename.endswith('.xlsx'):
        df = pd.read_excel(file)
        conn = sqlite3.connect('tools.db')
        df.to_sql('inventory_data', conn, if_exists='append', index=False)
        conn.close()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
