from flask import Flask, render_template, request, send_file
import psycopg2
import pandas as pd
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://attendance_user:hIEyKUeKKblpFAYtYXjcDp5GCXGQZcbl@dpg-d7b5hdjuibrs73b6m1d0-a.oregon-postgres.render.com/attendance_2cet"

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def to_int(val):
    try:
        return int(val)
    except:
        return 0

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
        absent INT,
        attendant TEXT
    )
    """)

    conn.commit()
    conn.close()

# ================== ENTRY ==================
@app.route("/", methods=["GET", "POST"])
def index():
    create_table()
    message = ""

    if request.method == "POST":
        try:
            floor = request.form.get("floor")
            date = request.form.get("date")
            attendant = request.form.get("attendant")
            floor_strength = to_int(request.form.get("floor_strength"))

            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                return render_template("index.html", floors=floors, years=years,
                                       message=f"❌ Already entered for {floor}")

            total_year_strength = 0
            valid = True

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                if (present + leave + absent) != strength:
                    valid = False

                total_year_strength += strength

                cur.execute("""
                INSERT INTO attendance (date,floor,year,strength,present,leave,absent,attendant)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date, floor, year, strength, present, leave, absent, attendant))

            if total_year_strength != floor_strength:
                valid = False

            if not valid:
                conn.rollback()
                message = "❌ Data mismatch!"
            else:
                conn.commit()
                message = "✅ Saved Successfully!"

            conn.close()

        except Exception as e:
            message = str(e)

    return render_template("index.html", floors=floors, years=years, message=message)

# ================== REPORT ==================
@app.route("/report", methods=["POST"])
def report():
    report_type = request.form.get("report_type")
    date = request.form.get("date")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT floor,year,strength,present,leave,absent,attendant
    FROM attendance WHERE date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "❌ No data found"

    data = {}
    grand = {"S":0,"P":0,"L":0,"A":0}

    year_summary = {y: {"S":0,"P":0,"L":0} for y in years}

    for floor,year,strength,present,leave,absent,attendant in rows:

        if floor not in data:
            data[floor] = {
                "years": {},
                "attendant": attendant,
                "total": {"S":0,"P":0,"L":0,"A":0}
            }

        data[floor]["years"][year] = {
            "S":strength,"P":present,"L":leave,"A":absent
        }

        # floor total
        data[floor]["total"]["S"] += strength
        data[floor]["total"]["P"] += present
        data[floor]["total"]["L"] += leave
        data[floor]["total"]["A"] += absent

        # grand total
        grand["S"] += strength
        grand["P"] += present
        grand["L"] += leave
        grand["A"] += absent

        # year summary
        year_summary[year]["S"] += strength
        year_summary[year]["P"] += present
        year_summary[year]["L"] += (leave+absent)

    return render_template("report.html",
                           data=data,
                           report_type=report_type,
                           year_summary=year_summary,
                           grand=grand,
                           date=date)

# ================== PDF ==================
@app.route("/download-pdf")
def download_pdf():
    date = request.args.get("date")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT floor,year,strength,present,leave,absent FROM attendance WHERE date=%s",(date,))
    rows = cur.fetchall()
    conn.close()

    file = "report.pdf"
    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("KING PALACE - 15", styles["Title"]))
    content.append(Paragraph(f"Date: {date}", styles["Normal"]))
    content.append(Spacer(1,10))

    for r in rows:
        content.append(Paragraph(str(r), styles["Normal"]))

    doc.build(content)

    return send_file(file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)