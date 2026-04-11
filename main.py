from flask import Flask, render_template, request, send_file
import psycopg2
import pandas as pd
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


def get_conn():
    return psycopg2.connect(DATABASE_URL)


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


def to_int(val):
    return int(val) if val and str(val).strip() else 0


# ================= HOME =================
@app.route("/", methods=["GET", "POST"])
def index():
    create_table()
    message = ""

    if request.method == "POST":
        try:
            floor = request.form.get("floor")
            date = request.form.get("date")
            hostel = "KING PALACE - 15"
            floor_strength = to_int(request.form.get("floor_strength"))

            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                message = f"❌ Already entered for {floor}"
                conn.close()
                return render_template("index.html", floors=floors, years=years, message=message)

            total_year_strength = 0

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                # VALIDATION
                if strength != (present + leave + absent):
                    conn.close()
                    return render_template("index.html",
                        floors=floors, years=years,
                        message=f"❌ Error in {year} calculation"
                    )

                total_year_strength += strength

                cur.execute("""
                INSERT INTO attendance (date, hostel, floor, year, strength, present, leave, absent)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date, hostel, floor, year, strength, present, leave, absent))

            if total_year_strength != floor_strength:
                conn.rollback()
                conn.close()
                return render_template("index.html",
                    floors=floors, years=years,
                    message="❌ Floor strength mismatch"
                )

            conn.commit()
            conn.close()
            message = "✅ Saved Successfully!"

        except Exception as e:
            message = str(e)

    return render_template("index.html", floors=floors, years=years, message=message)


# ================= REPORT =================
@app.route("/report", methods=["POST"])
def report():
    report_type = request.form.get("report_type")
    date = request.form.get("date")
    month = request.form.get("month")

    conn = get_conn()
    cur = conn.cursor()

    if date:
        cur.execute("""
        SELECT floor, year, strength, present, leave, absent
        FROM attendance WHERE date=%s
        """, (date,))
    else:
        cur.execute("""
        SELECT floor, year, strength, present, leave, absent
        FROM attendance WHERE TO_CHAR(date,'YYYY-MM')=%s
        """, (month,))

    rows = cur.fetchall()
    conn.close()

    data = {}
    year_summary = {y: {"Strength":0,"Present":0,"Leave":0} for y in years}

    total_strength = total_present = total_leave = 0

    for floor, year, strength, present, leave, absent in rows:

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
        date=date,
        month=month
    )


# ================= DOWNLOAD =================
@app.route("/download")
def download():
    date = request.args.get("date")
    format_type = request.args.get("type")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT floor, year, strength, present, leave, absent
    FROM attendance WHERE date=%s
    """, (date,))
    rows = cur.fetchall()
    conn.close()

    # ===== PDF =====
    if format_type == "pdf":
        file_name = f"report_{date}.pdf"
        doc = SimpleDocTemplate(file_name)
        styles = getSampleStyleSheet()
        content = []

        content.append(Paragraph("KING PALACE - 15", styles['Title']))
        content.append(Paragraph(f"Date: {date}", styles['Normal']))
        content.append(Spacer(1, 10))

        for r in rows:
            floor, year, s, p, l, a = r
            content.append(Paragraph(f"{floor} - {year} → S:{s} P:{p} L:{l} A:{a}", styles['Normal']))
            content.append(Spacer(1, 5))

        doc.build(content)
        return send_file(file_name, as_attachment=True)

    # ===== EXCEL =====
    df = pd.DataFrame(rows, columns=["Floor","Year","Strength","Present","Leave","Absent"])
    file = "report.xlsx"
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)