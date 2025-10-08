from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute('DELETE FROM inventory WHERE id=?', (item_id,))
conn.commit()
conn.close()
flash('✅ آیتم حذف شد.')
return redirect(url_for('index'))




# ------------------ Excel upload route ------------------
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
file = request.files.get('excel_file')
if not file or not file.filename:
flash('لطفاً یک فایل Excel انتخاب کنید.')
return redirect(url_for('index'))


_, ext = os.path.splitext(file.filename.lower())
if ext not in ALLOWED_EXCEL_EXT:
flash('پسوند فایل باید .xlsx یا .xls باشد.')
return redirect(url_for('index'))


filename = secure_filename(file.filename)
file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
file.save(file_path)


try:
df = pd.read_excel(file_path, engine='openpyxl')


expected_cols = ['id', 'tool_type', 'serial_number', 'size', 'thread_type', 'location', 'status', 'report_link']
if list(df.columns) != expected_cols:
flash('ساختار ستون‌های فایل اکسل مطابق انتظار نیست. ترتیب باید: ' + ','.join(expected_cols))
return redirect(url_for('index'))


conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
for _, row in df.iterrows():
vals = [None if (pd.isna(x)) else x for x in row.tolist()]
# اگر id خالی بود، از INSERT استفاده کن، در غیر این صورت REPLACE (به‌روزرسانی)
if vals[0] in (None, '', float('nan')):
cursor.execute('''
INSERT INTO inventory (tool_type, serial_number, size, thread_type, location, status, report_link)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', tuple(vals[1:]))
else:
# از REPLACE استفاده نمی‌کنیم چون schema با AUTOINCREMENT نیست؛ بهتر UPDATE یا INSERT OR REPLACE
cursor.execute('''
INSERT OR REPLACE INTO inventory (id, tool_type, serial_number, size, thread_type, location, status, report_link)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', tuple(vals))
conn.commit()
conn.close()
flash('✅ فایل اکسل با موفقیت پردازش و دیتابیس به‌روزرسانی شد.')
except Exception as e:
flash(f'❌ خطا هنگام پردازش فایل اکسل: {e}')


return redirect(url_for('index'))




# serve service worker from static root for correct scope
@app.route('/service-worker.js')
def service_worker():
return send_from_directory(os.path.join(BASE_DIR, 'static'), 'service-worker.js')




if __name__ == '__main__':
app.run(host='0.0.0.0', port=5000, debug=True)
