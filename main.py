from flask import Flask, render_template, request, send_file
import psycopg2
import pandas as pd
import os

app = Flask(__name__)

# 🔗 DATABASE (Render PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://attendance_user:hIEyKUeKKblpFAYtYXjcDp5GCXGQZcbl@dpg-d7b5hdjuibrs73b6m1d0-a.oregon-postgres.render.com/attendance_2cet"

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


# 🔌 DB CONNECTION
def get_conn():
    return psycopg2.connect(DATABASE_URL)


# 🔢 SAFE INT
def to_int(val):
    if val is None or str(val).strip() == "":
        return 0
    return int(val)

# 🛠 CREATE TABLE (AUTO)
def create_table():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        date DATE,
        hostel TEXT,
        floor TEXT,
        year TEXT,
        strength INT,
        present INT,
        leave INT,
        absent INT
    )
    """)

    conn.commit()
    conn.close()


# 🚀 HOME
@app.route("/", methods=["GET", "POST"])
def index():
    create_table()  # ensure table exists
    message = ""

    if request.method == "POST":
        try:
            floor = request.form.get("floor")
            date = request.form.get("date")
            hostel = request.form.get("hostel") or "KP-15"
            floor_strength = to_int(request.form.get("floor_strength"))

            conn = get_conn()
            cur = conn.cursor()

            # ❌ DUPLICATE CHECK
            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                message = f"❌ Data already punched for {floor} on {date}"
                conn.close()
                return render_template("index.html", floors=floors, years=years, message=message)

            total_year_strength = 0
            valid = True

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                # ✅ Validation
                if (present + leave + absent) != strength:
                    valid = False

                total_year_strength += strength

                cur.execute("""
                INSERT INTO attendance (date, hostel, floor, year, strength, present, leave, absent)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date, hostel, floor, year, strength, present, leave, absent))

            # ✅ Floor total validation
            if total_year_strength != floor_strength:
                valid = False

            if not valid:
                conn.rollback()
                message = "❌ Data mismatch! Please check values."
            else:
                conn.commit()
                message = "✅ Saved Successfully!"

            conn.close()

        except Exception as e:
            message = f"Error: {str(e)}"

    return render_template("index.html", floors=floors, years=years, message=message)


# 📊 REPORT (MONTH FILTER)
@app.route("/report", methods=["POST"])
def report():
    report_type = request.form.get("report_type")
    month = request.form.get("month")  # YYYY-MM

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT date,floor,year,strength,present,leave,absent
    FROM attendance
    WHERE TO_CHAR(date, 'YYYY-MM') = %s
    """, (month,))

    rows = cur.fetchall()
    conn.close()

    data = {}
    total_strength = total_present = total_leave = 0

    year_summary = {y: {"Strength":0, "Present":0, "Leave":0} for y in years}

    for date, floor, year, strength, present, leave, absent in rows:

        if floor not in data:
            data[floor] = {}

        data[floor][year] = {
            "Strength": strength,
            "Present": present,
            "Leave": leave,
            "Absent": absent
        }

        year_summary[year]["Strength"] += strength
        year_summary[year]["Present"] += present
        year_summary[year]["Leave"] += (leave + absent)

        total_strength += strength
        total_present += present
        total_leave += (leave + absent)

    return render_template("report.html",
                           data=data,
                           report_type=report_type,
                           total_strength=total_strength,
                           total_present=total_present,
                           total_leave=total_leave,
                           year_summary=year_summary,
                           month=month)


# 📥 EXCEL DOWNLOAD (MONTH FILTER)
@app.route("/download")
def download():
    month = request.args.get("month")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM attendance
        WHERE TO_CHAR(date, 'YYYY-MM') = %s
    """, (month,))

    rows = cur.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=[
        "ID","Date","Hostel","Floor","Year",
        "Strength","Present","Leave","Absent"
    ])

    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)


# ▶️ RUN
if __name__ == "__main__":
    app.run(debug=True)