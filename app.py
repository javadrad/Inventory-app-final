@app.route("/", methods=["GET"])
def index():
    query = "SELECT * FROM inventory WHERE 1=1"
    params = []

    tool_type = request.args.get("tool_type", "")
    status = request.args.get("status", "")
    location = request.args.get("location", "")
    size = request.args.get("size", "")
    thread_type = request.args.get("thread_type", "")

    if tool_type:
        query += " AND tool_type LIKE ?"
        params.append(f"%{tool_type}%")
    if status:
        query += " AND status LIKE ?"
        params.append(f"%{status}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if size:
        query += " AND size LIKE ?"
        params.append(f"%{size}%")
    if thread_type:
        query += " AND thread_type LIKE ?"
        params.append(f"%{thread_type}%")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    items = c.fetchall()
    conn.close()

    return render_template("index.html", items=items, tool_type=tool_type, status=status, location=location, size=size, thread_type=thread_type)
