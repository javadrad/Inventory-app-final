from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)

# مسیر ذخیره فایل‌ها
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ------------------- دیتابیس -------------------
def init_db():
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    quantity INTEGER,
                    location TEXT,
                    report_file TEXT
                )""")
    conn.commit()
    conn.close()

init_db()

# ------------------- روت‌ها -------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        quantity = request.form["quantity"]
        location = request.form["location"]

        # ذخیره فایل گزارش
        file = request.files.get("report")
        filename = None
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("INSERT INTO inventory (name, quantity, location, report_file) VALUES (?, ?, ?, ?)",
                  (name, quantity, location, filename))
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    items = c.fetchall()
    conn.close()

    return render_template("index.html", items=items)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ------------------- اجرا -------------------
if __name__ == "__main__":
    app.run(debug=True)
