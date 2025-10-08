from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import openpyxl
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret_key"

DATABASE = "inventory.db"
UPLOAD_FOLDER = os.path.join("static", "reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        excel_file = request.files.get("excel_file")
        if excel_file and excel_file.filename.endswith((".xlsx", ".xls")):
            try:
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                for i, row in enumerate(sheet.iter_rows(values_only=True)):
                    if i == 0:
                        continue
                    cursor.execute("""
                        INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                   (row[1], row[2], row[3], row[4], row[5], row[6], row[7]))
                conn.commit()
                conn.close()
                flash("بارگذاری Excel موفق بود.", "success")
            except Exception as e:
                flash(f"خطا در بارگذاری Excel: {e}", "error")
        else:
            flash("لطفاً یک فایل Excel انتخاب کنید.", "error")
        return redirect(url_for("index"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory")
    items = cursor.fetchall()
    conn.close()
    return render_template("index.html", items=items)

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
            report_path = os.path.join(UPLOAD_FOLDER, filename)
            report_file.save(report_path)
            report_link = f"/static/reports/{filename}"

        cursor.execute("""
            UPDATE inventory SET tool_type=?, serial_number=?, size=?, thread_type=?, location=?, status=?, report_link=?
            WHERE id=?""",
                       (tool_type, serial_number, size, thread_type, location, status, report_link, item_id))
        conn.commit()
        conn.close()
        flash("ویرایش موفق بود.", "success")
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
    flash("حذف انجام شد.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
