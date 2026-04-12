from flask import Flask, render_template, request, send_file
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


# 🔌 DB CONNECTION
def get_conn():
    return psycopg2.connect(DATABASE_URL)


# 🔢 SAFE INT
def to_int(val):
    try:
        return int(val)
    except:
        return 0


# 🛠 CREATE / FIX TABLE
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

    # 🔥 FIX OLD DB (ADD COLUMN IF MISSING)
    cur.execute("""
    ALTER TABLE attendance
    ADD COLUMN IF NOT EXISTS attendant TEXT
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
            floor = request.form.get("floor")
            date = request.form.get("date")
            attendant = request.form.get("attendant")
            hostel = "KING PALACE - 15"
            floor_strength = to_int(request.form.get("floor_strength"))

            if not floor or not date or not attendant:
                return render_template("index.html", floors=floors, years=years,
                                       message="❌ Fill all fields")

            conn = get_conn()
            cur = conn.cursor()

            # ❌ DUPLICATE CHECK
            cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
            if cur.fetchone():
                conn.close()
                return render_template("index.html", floors=floors, years=years,
                                       message=f"❌ Already entered for {floor}")

            total_strength = 0
            valid = True

            for year in years:
                s = to_int(request.form.get(f"{year}_strength"))
                p = to_int(request.form.get(f"{year}_present"))
                l = to_int(request.form.get(f"{year}_leave"))
                a = to_int(request.form.get(f"{year}_absent"))

                if (p + l + a) != s:
                    valid = False

                total_strength += s

                cur.execute("""
                INSERT INTO attendance (date, hostel, floor, year, strength, present, leave, absent, attendant)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date, hostel, floor, year, s, p, l, a, attendant))

            if total_strength != floor_strength:
                valid = False

            if not valid:
                conn.rollback()
                message = "❌ Data mismatch!"
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

    # 🔥 IMPORTANT FIX (handle NULL attendant)
    cur.execute("""
    SELECT floor, year, strength, present, leave, absent, COALESCE(attendant,'N/A')
    FROM attendance
    WHERE date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "❌ No data found"

    data = {}
    floor_totals = {}
    grand = {"S":0, "P":0, "L":0, "A":0}
    year_summary = {y: {"Strength":0, "Present":0, "Leave":0} for y in years}

    for floor, year, s, p, l, a, att in rows:

        if floor not in data:
            data[floor] = {"years": {}, "attendant": att}
            floor_totals[floor] = {"S":0, "P":0, "L":0, "A":0}

        data[floor]["years"][year] = {
            "S": s, "P": p, "L": l, "A": a
        }

        floor_totals[floor]["S"] += s
        floor_totals[floor]["P"] += p
        floor_totals[floor]["L"] += l
        floor_totals[floor]["A"] += a

        grand["S"] += s
        grand["P"] += p
        grand["L"] += l
        grand["A"] += a

        year_summary[year]["Strength"] += s
        year_summary[year]["Present"] += p
        year_summary[year]["Leave"] += (l + a)

    return render_template("report.html",
                           data=data,
                           floor_totals=floor_totals,
                           grand=grand,
                           year_summary=year_summary,
                           report_type=report_type,
                           date=date)


# 📄 PDF
@app.route("/download-pdf")
def download_pdf():
    return "PDF feature coming soon"


# ▶️ RUN
if __name__ == "__main__":
    app.run(debug=True)