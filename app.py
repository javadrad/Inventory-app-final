from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from openpyxl import load_workbook

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join("static", "reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DATABASE = "inventory.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
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
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET"])
def index():
    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

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

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()
    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, size=size)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]

    report_file = request.files.get("report_file")
    report_link = ""
    if report_file and report_file.filename.endswith(".pdf"):
        filename = secure_filename(report_file.filename)
        report_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        report_file.save(report_path)
        report_link = f"/static/reports/{filename}"

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (tool_type, serial_number, size, thread_type, location, status, report_link))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))

@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    try:
        file = request.files["excel_file"]
        if file and file.filename.endswith((".xlsx", ".xls")):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)

            wb = load_workbook(path)
            ws = wb.active

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if len(row) != 6:
                    return f"خطا در سطر {row_idx}: تعداد ستون‌ها باید 6 باشد، اما {len(row)} یافت شد."
                row = tuple("" if v is None else v for v in row)
                cursor.execute("""
                    INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                               (*row, ""))
            conn.commit()
            conn.close()
            wb.close()
            return redirect(url_for("index"))

        return "فایل اکسل معتبر نیست!"

    except Exception as e:
        return f"خطا در پردازش اکسل: {str(e)}"

@app.route("/upload_report/<int:item_id>", methods=["POST"])
def upload_report(item_id):
    report_file = request.files.get("report_file")
    if report_file and report_file.filename.endswith(".pdf"):
        filename = secure_filename(report_file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        report_file.save(path)
        report_link = f"/static/reports/{filename}"

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET report_link=? WHERE id=?", (report_link, item_id))
        conn.commit()
        conn.close()

    return redirect(url_for("index"))

@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        tool_type = request.form["tool_type"]
        serial_number = request.form["serial_number"]
        size = request.form["size"]
        thread_type = request.form["thread_type"]
        location = request.form["location"]
        status = request.form["status"]

        report_link = request.form.get("report_link", "")
        report_file = request.files.get("report_file")

        if report_file and report_file.filename.endswith(".pdf"):
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            report_file.save(report_path)
            report_link = f"/static/reports/{filename}"

        cursor.execute("""
            UPDATE inventory
            SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
            WHERE id=?""",
                       (tool_type, serial_number, size, thread_type, location, status, report_link, item_id))

        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    return render_template("edit.html", item=item)

@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
