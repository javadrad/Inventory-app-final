from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import sqlite3
import os
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret-key-tool-manager"

# مسیر پوشه آپلود گزارش‌ها
UPLOAD_FOLDER = os.path.join("static", "reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DATABASE = "inventory.db"

# ایجاد دیتابیس اگر وجود نداشته باشد
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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # بارگذاری فایل اکسل
        excel_file = request.files.get("excel_file")
        if excel_file and excel_file.filename.endswith((".xlsx", ".xls")):
            filename = secure_filename(excel_file.filename)
            file_path = os.path.join("static", filename)
            excel_file.save(file_path)

            try:
                df = pd.read_excel(file_path, engine="openpyxl")
                required_cols = ["id", "tool_type", "serial_number", "size", "thread_type", "location", "status", "report_link"]
                if list(df.columns) != required_cols:
                    flash("ساختار فایل اکسل نادرست است!", "error")
                    return redirect(url_for("index"))

                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT OR REPLACE INTO inventory
                        (id, tool_type, serial_number, size, thread_type, location, status, report_link)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(row))
                conn.commit()
                conn.close()
                flash("بارگذاری و بروزرسانی دیتابیس با موفقیت انجام شد ✅", "success")
            except Exception as e:
                flash(f"خطا در خواندن فایل اکسل: {e}", "error")
            os.remove(file_path)
        return redirect(url_for("index"))

    # نمایش ابزارها و جستجو
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
    size = request.args.get("size", "")

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

    flash("ابزار با موفقیت اضافه شد ✅", "success")
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

        report_file = request.files.get("report_file")
        report_link = request.form.get("report_link", "")

        if report_file and report_file.filename.endswith(".pdf"):
            filename = secure_filename(report_file.filename)
            report_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            report_file.save(report_path)
            report_link = f"/static/reports/{filename}"

        cursor.execute("""
            UPDATE inventory SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
            WHERE id=?""",
                       (tool_type, serial_number, size, thread_type, location, status, report_link, item_id))
        conn.commit()
        conn.close()
        flash("ویرایش ابزار با موفقیت انجام شد ✅", "success")
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
    flash("ابزار حذف شد ❌", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
