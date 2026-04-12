from flask import Flask, render_template, request, send_file
import psycopg2
import pandas as pd
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://attendance_user:hIEyKUeKKblpFAYtYXjcDp5GCXGQZcbl@dpg-d7b5hdjuibrs73b6m1d0-a.oregon-postgres.render.com/attendance_2cet"

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


# 🔌 DB CONNECTION
def get_conn():
    return psycopg2.connect(DATABASE_URL)


# 🔢 SAFE INT
def to_int(val):
    return int(val) if val and str(val).strip() else 0


# 🛠 CREATE TABLE + AUTO FIX
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

    # ✅ AUTO ADD COLUMN (IMPORTANT FIX)
    try:
        cur.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS attendant TEXT;")
    except:
        pass

    conn.commit()
    conn.close()


# 🚀 HOME
@app.route("/", methods=["GET", "POST"])
def index():
    create_table()
    message = ""

    if request.method == "POST":
        try:
            floor = request.form.get("floor")
            date = request.form.get("date")
            hostel = "KING PALACE - 15"
            attendant = request.form.get("attendant")
            floor_strength = to_int(request.form.get("floor_strength"))

            conn = get_conn()
            cur = conn.cursor()

            # ❌ DUPLICATE CHECK
            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                message = f"❌ Already entered for {floor} on {date}"
                conn.close()
                return render_template("index.html", floors=floors, years=years, message=message)

            total_year_strength = 0
            valid = True

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                # ❌ VALIDATION
                if strength != (present + leave + absent):
                    valid = False

                total_year_strength += strength

                # ✅ SAFE INSERT
                try:
                    cur.execute("""
                    INSERT INTO attendance 
                    (date,hostel,floor,year,strength,present,leave,absent,attendant)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (date, hostel, floor, year, strength, present, leave, absent, attendant))
                except:
                    cur.execute("""
                    INSERT INTO attendance 
                    (date,hostel,floor,year,strength,present,leave,absent)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (date, hostel, floor, year, strength, present, leave, absent))

            # ❌ FLOOR VALIDATION
            if floor_strength != total_year_strength:
                valid = False

            if not valid:
                conn.rollback()
                message = "❌ Error: Check Strength / Present / Leave / Absent"
            else:
                conn.commit()
                message = "✅ Saved Successfully!"

            conn.close()

        except Exception as e:
            message = f"Error: {str(e)}"

    return render_template("index.html", floors=floors, years=years, message=message)


# 📊 REPORT
@app.route("/report", methods=["POST"])
def report():
    date = request.form.get("date")
    month = request.form.get("month")
    report_type = request.form.get("report_type")

    conn = get_conn()
    cur = conn.cursor()

    if date:
        cur.execute("""
        SELECT date,floor,year,strength,present,leave,absent,attendant
        FROM attendance
        WHERE date=%s
        """, (date,))
    else:
        cur.execute("""
        SELECT date,floor,year,strength,present,leave,absent,attendant
        FROM attendance
        WHERE TO_CHAR(date, 'YYYY-MM')=%s
        """, (month,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return render_template("report.html", message="❌ No data found")

    data = {}
    grand = {"strength":0, "present":0, "leave":0, "absent":0}
    attendants = {}

    for d, floor, year, strength, present, leave, absent, attendant in rows:

        if floor not in data:
            data[floor] = {}
            attendants[floor] = attendant

        data[floor][year] = {
            "Strength": strength,
            "Present": present,
            "Leave": leave,
            "Absent": absent
        }

        grand["strength"] += strength
        grand["present"] += present
        grand["leave"] += leave
        grand["absent"] += absent

    return render_template("report.html",
                           data=data,
                           attendants=attendants,
                           grand=grand,
                           report_type=report_type,
                           date=date,
                           month=month)


# 📥 EXCEL DOWNLOAD
@app.route("/download")
def download():
    date = request.args.get("date")
    month = request.args.get("month")

    conn = get_conn()
    cur = conn.cursor()

    if date:
        cur.execute("SELECT * FROM attendance WHERE date=%s", (date,))
    else:
        cur.execute("SELECT * FROM attendance WHERE TO_CHAR(date,'YYYY-MM')=%s", (month,))

    rows = cur.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=[
        "ID","Date","Hostel","Floor","Year",
        "Strength","Present","Leave","Absent","Attendant"
    ])

    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)


# ▶️ RUN
if __name__ == "__main__":
    app.run(debug=True)