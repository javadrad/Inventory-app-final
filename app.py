from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
from openpyxl import load_workbook
app = Flask(__name__)
DB_PATH = "tools_data.db"

# ایجاد دیتابیس در صورت عدم وجود
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS inventory_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_type TEXT,
            serial_number TEXT UNIQUE,
            size TEXT,
            thread_type TEXT,
            location TEXT,
            status TEXT,
            report_link TEXT,
            description TEXT
        )''')
        conn.commit()

init_db()

# صفحه اصلی
@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory_data")
    data = c.fetchall()
    conn.close()
    return render_template("index.html", data=data)

# افزودن ابزار جدید به صورت دستی
@app.route("/add", methods=["POST"])
def add_tool():
    data = (
        request.form["tool_type"],
        request.form["serial_number"],
        request.form["size"],
        request.form["thread_type"],
        request.form["location"],
        request.form["status"],
        request.form["report_link"],
        request.form.get("description", "")
    )

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # جلوگیری از ثبت تکراری بر اساس شماره سریال
        c.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number=?", (data[1],))
        if c.fetchone()[0] > 0:
            return jsonify({"success": False, "message": "رکوردی با این شماره سریال قبلاً ثبت شده است."})
        c.execute("INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data)
        conn.commit()
    return redirect("/")

# آپلود فایل Excel و وارد کردن داده‌ها
@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files["file"]
    if not file:
        return redirect("/")

    df = pd.read_excel(file)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    required_cols = {"tool_type", "serial_number", "size", "thread_type", "location", "status", "report_link", "description"}
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        for _, row in df.iterrows():
            serial = str(row["serial_number"]).strip()
            c.execute("SELECT COUNT(*) FROM inventory_data WHERE serial_number=?", (serial,))
            if c.fetchone()[0] == 0:  # فقط اگر تکراری نبود
                c.execute(
                    "INSERT INTO inventory_data (tool_type, serial_number, size, thread_type, location, status, report_link, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["tool_type"], serial, row["size"], row["thread_type"],
                        row["location"], row["status"], row["report_link"], row["description"]
                    )
                )
        conn.commit()
    return redirect("/")

# حذف ابزار موردی
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM inventory_data WHERE id=?", (item_id,))
        conn.commit()
    return jsonify({"success": True})

# حذف همه ابزارها (فیلتر شده یا کل دیتابیس)
@app.route("/delete_all", methods=["POST"])
def delete_all():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM inventory_data")
        conn.commit()
    return jsonify({"success": True})

# جستجو
@app.route("/search", methods=["GET"])
def search():
    filters = []
    params = []
    if request.args.get("tool_type"):
        filters.append("tool_type=?")
        params.append(request.args["tool_type"])
    if request.args.get("serial_number"):
        filters.append("serial_number LIKE ?")
        params.append(f"%{request.args['serial_number']}%")
    if request.args.get("status"):
        filters.append("status=?")
        params.append(request.args["status"])
    if request.args.get("location"):
        filters.append("location LIKE ?")
        params.append(f"%{request.args['location']}%")

    query = "SELECT * FROM inventory_data"
    if filters:
        query += " WHERE " + " AND ".join(filters)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.close()
    return jsonify(data)

# ذخیره خودکار توضیحات
@app.route("/update_description/<int:item_id>", methods=["POST"])
def update_description(item_id):
    desc = request.json.get("description", "")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE inventory_data SET description=? WHERE id=?", (desc, item_id))
        conn.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
