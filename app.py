from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os
from werkzeug.utils import secure_filename
import csv

app = Flask(__name__)
app.secret_key = "inventory_secret"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "inventory.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ایجاد دیتابیس در صورت عدم وجود
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

# صفحه اصلی
@app.route("/")
def index():
    search = request.args.get("search", "")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """SELECT * FROM inventory_data 
               WHERE tool_type LIKE ? OR serial_number LIKE ? 
               OR location LIKE ? OR status LIKE ?"""
    c.execute(query, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
    data = c.fetchall()
    conn.close()
    return render_template("index.html", data=data, search=search)

# ثبت ابزار
@app.route("/add", methods=["POST"])
def add_tool():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]
    description = request.form.get("description", "")
    file = request.files.get("report_file")

    report_link = ""
    if file and file.filename:
        filename = secure_filename(file.filename)
        report_link = os.path.join("reports", filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (tool_type, serial_number, size, thread_type, location, status, report_link, description))
    conn.commit()
    conn.close()
    flash("✅ ابزار با موفقیت اضافه شد", "success")
    return redirect(url_for("index"))

# حذف ابزار
@app.route("/delete/<int:id>")
def delete_tool(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM inventory_data WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("🗑️ ابزار حذف شد", "danger")
    return redirect(url_for("index"))

# ویرایش ابزار
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_tool(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form["size"]
        thread_type = request.form["thread_type"]
        location = request.form["location"]
        status = request.form["status"]
        description = request.form["description"]
        c.execute("""UPDATE inventory_data SET tool_type=?, serial_number=?, size=?, 
                     thread_type=?, location=?, status=?, description=? WHERE id=?""",
                  (tool_type, serial_number, size, thread_type, location, status, description, id))
        conn.commit()
        conn.close()
        flash("✏️ ویرایش انجام شد", "info")
        return redirect(url_for("index"))
    else:
        c.execute("SELECT * FROM inventory_data WHERE id=?", (id,))
        tool = c.fetchone()
        conn.close()
        return render_template("edit.html", tool=tool)

# آپلود فایل اکسل (CSV)
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or not file.filename.endswith(".csv"):
        flash("⚠️ لطفاً فایل CSV معتبر انتخاب کنید", "warning")
        return redirect(url_for("index"))

    filepath = os.path.join(BASE_DIR, secure_filename(file.filename))
    file.save(filepath)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # رد کردن هدر
        for row in reader:
            if len(row) < 7:
                continue
            c.execute("""INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (row[1], row[2], row[3], row[4], row[5], row[6], "", ""))
    conn.commit()
    conn.close()
    os.remove(filepath)
    flash("✅ فایل CSV با موفقیت بارگذاری شد", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
