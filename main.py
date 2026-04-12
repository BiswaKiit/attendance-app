from flask import Flask, render_template, request, send_file
import psycopg2
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


# 🔌 DB
def get_conn():
    return psycopg2.connect(DATABASE_URL)


# 🔢 SAFE INT
def to_int(val):
    if val is None or val == "":
        return None
    return int(val)


# 🛠 CREATE TABLE
def create_table():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        date DATE,
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


# 🚀 HOME
@app.route("/", methods=["GET", "POST"])
def index():
    create_table()
    message = ""

    if request.method == "POST":
        try:
            date = request.form.get("date")
            floor = request.form.get("floor")
            attendant = request.form.get("attendant")
            floor_strength = to_int(request.form.get("floor_strength"))

            if not date or not floor or not attendant or floor_strength is None:
                return render_template("index.html", floors=floors, years=years,
                                       message="❌ Fill all fields")

            conn = get_conn()
            cur = conn.cursor()

            total_year_strength = 0
            valid = True

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                # ❌ EMPTY CHECK
                if None in [strength, present, leave, absent]:
                    valid = False

                # ❌ LOGIC CHECK
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
                message = "❌ Invalid data! Check all values."
            else:
                conn.commit()
                message = "✅ Saved Successfully!"

            conn.close()

        except Exception as e:
            message = f"❌ Error: {str(e)}"

    return render_template("index.html", floors=floors, years=years, message=message)


# 📊 REPORT
@app.route("/report", methods=["POST"])
def report():
    report_type = request.form.get("report_type")
    date = request.form.get("date")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT floor,year,strength,present,leave,absent,attendant
    FROM attendance
    WHERE date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "❌ No data found"

    data = {}
    floor_totals = {}
    grand = {"S":0,"P":0,"L":0,"A":0}

    for floor, year, s, p, l, a, att in rows:

        if floor not in data:
            data[floor] = {}
            floor_totals[floor] = {"S":0,"P":0,"L":0,"A":0,"attendant":att}

        data[floor][year] = {"S":s,"P":p,"L":l,"A":a}

        floor_totals[floor]["S"] += s
        floor_totals[floor]["P"] += p
        floor_totals[floor]["L"] += l
        floor_totals[floor]["A"] += a

        grand["S"] += s
        grand["P"] += p
        grand["L"] += l
        grand["A"] += a

    total_leave = grand["L"] + grand["A"]

    return render_template("report.html",
                           data=data,
                           floor_totals=floor_totals,
                           grand=grand,
                           total_leave=total_leave,
                           report_type=report_type,
                           date=date)


# 📄 PDF
@app.route("/download-pdf")
def download_pdf():
    date = request.args.get("date")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT floor,year,strength,present,leave,absent
    FROM attendance WHERE date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    file = "report.pdf"
    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("KING PALACE - 15", styles["Title"]))
    content.append(Spacer(1, 10))

    total_s = total_p = total_l = total_a = 0

    for r in rows:
        floor, year, s, p, l, a = r
        content.append(Paragraph(f"{floor} | {year} → S:{s} P:{p} L:{l} A:{a}", styles["Normal"]))

        total_s += s
        total_p += p
        total_l += l
        total_a += a

    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Total Strength: {total_s}", styles["Normal"]))
    content.append(Paragraph(f"Total Present: {total_p}", styles["Normal"]))
    content.append(Paragraph(f"Total Leave: {total_l + total_a}", styles["Normal"]))

    doc.build(content)

    return send_file(file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)