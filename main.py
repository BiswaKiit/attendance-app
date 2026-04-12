from flask import Flask, render_template, request, send_file
import psycopg2
import os

# PDF
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


# ✅ CREATE TABLE SAFE
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
            attendant = request.form.get("attendant")

            # ✅ STRICT VALIDATION (no blank allowed)
            if not floor or not date or not attendant:
                return render_template("index.html", floors=floors, years=years,
                                       message="❌ Fill all fields")

            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                conn.close()
                return render_template("index.html", floors=floors, years=years,
                                       message=f"❌ Already entered for {floor}")

            total_year_strength = 0

            for year in years:
                strength = request.form.get(f"{year}_strength")
                present = request.form.get(f"{year}_present")
                leave = request.form.get(f"{year}_leave")
                absent = request.form.get(f"{year}_absent")

                # ❌ NO EMPTY ALLOWED
                if "" in [strength, present, leave, absent]:
                    conn.close()
                    return render_template("index.html", floors=floors, years=years,
                                           message="❌ Fill all cells (use 0 if needed)")

                strength = to_int(strength)
                present = to_int(present)
                leave = to_int(leave)
                absent = to_int(absent)

                # ❌ VALIDATION
                if (present + leave + absent) != strength:
                    conn.close()
                    return render_template("index.html", floors=floors, years=years,
                                           message="❌ Year data mismatch")

                total_year_strength += strength

                cur.execute("""
                INSERT INTO attendance 
                (date, hostel, floor, year, strength, present, leave, absent, attendant)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date, hostel, floor, year, strength, present, leave, absent, attendant))

            # ❌ FLOOR VALIDATION
            if total_year_strength != floor_strength:
                conn.rollback()
                conn.close()
                return render_template("index.html", floors=floors, years=years,
                                       message="❌ Floor strength mismatch")

            conn.commit()
            conn.close()

            message = "✅ Saved Successfully!"

        except Exception as e:
            message = f"❌ Error: {str(e)}"

    return render_template("index.html", floors=floors, years=years, message=message)


# ✅ FIXED REPORT (TOTAL CALCULATION FIXED HERE)
@app.route("/report", methods=["POST"])
def report():
    try:
        report_type = request.form.get("report_type")
        date = request.form.get("date")

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
            return "❌ No data found"

        data = {}
        attendants = {}

        grand = {"strength": 0, "present": 0, "leave": 0, "absent": 0}

        # ✅ FIX: PRE-CALCULATE FLOOR TOTALS
        floor_totals = {}

        for floor, year, strength, present, leave, absent, attendant in rows:

            if floor not in data:
                data[floor] = {}
                attendants[floor] = attendant
                floor_totals[floor] = {"s": 0, "p": 0, "l": 0, "a": 0}

            data[floor][year] = {
                "Strength": strength,
                "Present": present,
                "Leave": leave,
                "Absent": absent
            }

            # ✅ FLOOR TOTALS
            floor_totals[floor]["s"] += strength
            floor_totals[floor]["p"] += present
            floor_totals[floor]["l"] += leave
            floor_totals[floor]["a"] += absent

            # ✅ GRAND TOTAL
            grand["strength"] += strength
            grand["present"] += present
            grand["leave"] += leave
            grand["absent"] += absent

        return render_template(
            "report.html",
            data=data,
            attendants=attendants,
            grand=grand,
            floor_totals=floor_totals,
            report_type=report_type,
            date=date
        )

    except Exception as e:
        return f"❌ ERROR: {str(e)}"


# ✅ PDF DOWNLOAD ONLY
@app.route("/download-pdf")
def download_pdf():
    date = request.args.get("date")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT strength, present, leave, absent
    FROM attendance
    WHERE date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    file_path = "report.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    total_strength = sum(r[0] for r in rows)
    total_present = sum(r[1] for r in rows)
    total_leave = sum(r[2] + r[3] for r in rows)

    content = [
        Paragraph("KING PALACE - 15", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"Date: {date}", styles["Normal"]),
        Spacer(1, 10),
        Paragraph(f"Total Strength: {total_strength}", styles["Normal"]),
        Paragraph(f"Total Present: {total_present}", styles["Normal"]),
        Paragraph(f"Total Leave: {total_leave}", styles["Normal"]),
    ]

    doc.build(content)

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)