from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
import openpyxl

app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DATABASE = os.path.join(BASE_DIR, "inventory.db")


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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tool_type = request.args.get("tool_type", "")
    serial_number = request.args.get("serial_number", "")
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
    if status:
        query += " AND status LIKE ?"
        params.append(f"%{status}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()

    return render_template("index.html", items=items, tool_type=tool_type,
                           serial_number=serial_number, status=status, location=location)


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
    if report_file and report_file.filename != "":
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

    flash("ابزار با موفقیت اضافه شد!", "success")
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

        report_file = request.files.get("report_link")
        report_link = request.form.get("report_link", "")

        if report_file and report_file.filename != "":
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
        flash("ویرایش با موفقیت انجام شد!", "success")
        return redirect(url_for("index"))

    cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
    tool = cursor.fetchone()
    conn.close()
    return render_template("edit.html", tool=tool)


@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("ابزار حذف شد!", "danger")
    return redirect(url_for("index"))


@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if not file or file.filename == "":
        flash("فایل اکسل انتخاب نشده است", "danger")
        return redirect(url_for("index"))

    if not file.filename.endswith((".xlsx", ".xls")):
        flash("لطفاً یک فایل اکسل معتبر انتخاب کنید", "danger")
        return redirect(url_for("index"))

    wb = openpyxl.load_workbook(file)
    sheet = wb.active
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    row_num = 1
    try:
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) < 6:
                flash(f"خطا در سطر {row_num}: تعداد ستون‌ها کمتر از حد لازم است", "danger")
                continue
            tool_type, serial_number, size, thread_type, location, status = row[:6]
            cursor.execute("""
                INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                VALUES (?, ?, ?, ?, ?, ?, '')""",
                           (tool_type, serial_number, size, thread_type, location, status))
            row_num += 1
        conn.commit()
    except Exception as e:
        flash(f"خطا در پردازش فایل اکسل: {str(e)}", "danger")
    finally:
        conn.close()

    flash("فایل اکسل با موفقیت بارگذاری شد!", "success")
    return redirect(url_for("index"))


@app.route("/reports/<path:filename>")
def reports(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
