from flask import Flask, render_template, request, send_file
import psycopg2
import pandas as pd
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# 🔗 DATABASE
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://attendance_user:hIEyKUeKKblpFAYtYXjcDp5GCXGQZcbl@dpg-d7b5hdjuibrs73b6m1d0-a.oregon-postgres.render.com/attendance_2cet"

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


# 🔌 DB CONNECTION
def get_conn():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print("DB ERROR:", e)
        return None


# 🔢 SAFE INT
def to_int(val):
    try:
        return int(val)
    except:
        return 0


# 🛠 CREATE TABLE + ADD COLUMN (AUTO FIX)
def create_table():
    conn = get_conn()
    if not conn:
        return
    cur = conn.cursor()

    # Create table
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

    # Add attendant column if not exists
    try:
        cur.execute("ALTER TABLE attendance ADD COLUMN attendant TEXT")
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
            hostel = request.form.get("hostel") or "KING PALACE - 15"
            floor_strength = to_int(request.form.get("floor_strength"))
            attendant = request.form.get("attendant") or ""

            if not floor or not date:
                return render_template("index.html", floors=floors, years=years,
                                       message="❌ Select floor & date")

            conn = get_conn()
            if not conn:
                return render_template("index.html", floors=floors, years=years,
                                       message="❌ DB connection failed")

            cur = conn.cursor()

            # ❌ DUPLICATE CHECK
            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                conn.close()
                return render_template("index.html", floors=floors, years=years,
                                       message=f"❌ Already entered for {floor}")

            total_year_strength = 0
            valid = True

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                # VALIDATION
                if (present + leave + absent) != strength:
                    valid = False

                total_year_strength += strength

                cur.execute("""
                INSERT INTO attendance 
                (date, hostel, floor, year, strength, present, leave, absent, attendant)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date, hostel, floor, year, strength, present, leave, absent, attendant))

            # FLOOR VALIDATION
            if total_year_strength != floor_strength:
                valid = False

            if not valid:
                conn.rollback()
                message = "❌ Data mismatch! Check values."
            else:
                conn.commit()
                message = "✅ Saved Successfully!"

            conn.close()

        except Exception as e:
            message = f"❌ Error: {str(e)}"

    return render_template("index.html", floors=floors, years=years, message=message)


# 📊 REPORT (DATE BASED)
@app.route("/report", methods=["POST"])
def report():
    try:
        report_type = request.form.get("report_type")
        date = request.form.get("date")

        if not date:
            return "❌ Please select date"

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        SELECT floor, year, strength, present, leave, absent, attendant
        FROM attendance
        WHERE date=%s
        """, (date,))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            return "❌ No data found for this date"

        data = {}
        attendants = {}

        grand = {
            "strength": 0,
            "present": 0,
            "leave": 0,
            "absent": 0
        }

        year_summary = {y: {"Strength": 0, "Present": 0, "Leave": 0} for y in years}

        for floor, year, strength, present, leave, absent, attendant in rows:

            if floor not in data:
                data[floor] = {}
                attendants[floor] = attendant

            data[floor][year] = {
                "Strength": strength,
                "Present": present,
                "Leave": leave,
                "Absent": absent
            }

            # Year summary (for Part Report)
            year_summary[year]["Strength"] += strength
            year_summary[year]["Present"] += present
            year_summary[year]["Leave"] += (leave + absent)

            # Grand totals
            grand["strength"] += strength
            grand["present"] += present
            grand["leave"] += leave
            grand["absent"] += absent

        return render_template(
            "report.html",
            data=data,
            report_type=report_type,
            date=date,
            attendants=attendants,
            grand=grand,
            year_summary=year_summary
        )

    except Exception as e:
        return f"❌ ERROR: {str(e)}"


# 📥 PDF DOWNLOAD
@app.route("/download-pdf")
def download_pdf():
    date = request.args.get("date")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT floor, year, strength, present, leave, absent
    FROM attendance
    WHERE date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    file_path = "report.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("KING PALACE - 15", styles["Title"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Date: {date}", styles["Normal"]))
    content.append(Spacer(1, 10))

    total_strength = total_present = total_leave = 0

    for floor, year, strength, present, leave, absent in rows:
        content.append(Paragraph(
            f"{floor} | {year} → S:{strength} P:{present} L:{leave} A:{absent}",
            styles["Normal"]
        ))

        total_strength += strength
        total_present += present
        total_leave += (leave + absent)

    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Total Strength: {total_strength}", styles["Normal"]))
    content.append(Paragraph(f"Total Present: {total_present}", styles["Normal"]))
    content.append(Paragraph(f"Total Leave: {total_leave}", styles["Normal"]))

    doc.build(content)

    return send_file(file_path, as_attachment=True)


# ▶️ RUN
if __name__ == "__main__":
    app.run(debug=True)