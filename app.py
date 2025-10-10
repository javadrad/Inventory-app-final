from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import pandas as pd
from werkzeug.utils import secure_filename

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
            report_link TEXT,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET"])
def index():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")
    status = request.args.get("status", "")
    location = request.args.get("location", "")

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
        query += " AND status LIKE ?"
        params.append(f"%{status}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()

    return render_template("index.html", items=items, tool_type=tool_type, serial_number=serial_number, size=size, status=status, location=location)

@app.route("/add", methods=["POST"])
def add():
    tool_type = request.form["tool_type"]
    serial_number = request.form["serial_number"]
    size = request.form["size"]
    thread_type = request.form["thread_type"]
    location = request.form["location"]
    status = request.form["status"]
    description = request.form.get("description", "")

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
        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (tool_type, serial_number, size, thread_type, location, status, report_link, description))
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
        description = request.form.get("description", "")

        report_file = request.files.get("report_file")
        report_link = request.form.get("report_link", "")

        if report_file and report_file.filename.endswith(".pdf"):
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            report_file.save(report_path)
            report_link = f"/static/reports/{filename}"

        cursor.execute("""
            UPDATE inventory SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?, description=?
            WHERE id=?""",
                       (tool_type, serial_number, size, thread_type, location, status, report_link, description, item_id))
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

@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if file and file.filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file)
        conn = sqlite3.connect(DATABASE)
        for _, row in df.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                           (row.get("tool_type"), row.get("serial_number"), row.get("size"),
                            row.get("thread_type"), row.get("location"), row.get("status"),
                            row.get("report_link"), row.get("description")))
        conn.commit()
        conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
