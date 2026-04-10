from flask import Flask, render_template, request, send_file
import psycopg2
import pandas as pd
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def to_int(val):
    return int(val) if val and str(val).strip() else 0

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

@app.route("/", methods=["GET", "POST"])
def index():
    create_table()
    message = ""

    if request.method == "POST":
        floor = request.form.get("floor")
        date = request.form.get("date")
        hostel = request.form.get("hostel")

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM attendance WHERE date=%s AND floor=%s", (date, floor))
        if cur.fetchone():
            message = "Already entered"
            conn.close()
            return render_template("index.html", floors=floors, years=years)

        for year in years:
            cur.execute("""
            INSERT INTO attendance (date, hostel, floor, year, strength, present, leave, absent)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                date, hostel, floor, year,
                to_int(request.form.get(f"{year}_strength")),
                to_int(request.form.get(f"{year}_present")),
                to_int(request.form.get(f"{year}_leave")),
                to_int(request.form.get(f"{year}_absent"))
            ))

        conn.commit()
        conn.close()

    return render_template("index.html", floors=floors, years=years)

@app.route("/report", methods=["POST"])
def report():
    report_type = request.form.get("report_type")
    date = request.form.get("date")
    month = request.form.get("month")

    conn = get_conn()
    cur = conn.cursor()

    if date:
        cur.execute("SELECT * FROM attendance WHERE date=%s", (date,))
    elif month:
        cur.execute("SELECT * FROM attendance WHERE TO_CHAR(date,'YYYY-MM')=%s", (month,))
    else:
        cur.execute("SELECT * FROM attendance")

    rows = cur.fetchall()
    conn.close()

    total_strength = sum(r[5] for r in rows)
    total_present = sum(r[6] for r in rows)
    total_leave = sum(r[7]+r[8] for r in rows)

    return render_template("report.html",
                           total_strength=total_strength,
                           total_present=total_present,
                           total_leave=total_leave,
                           month=month)

@app.route("/download")
def download():
    month = request.args.get("month")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM attendance WHERE TO_CHAR(date,'YYYY-MM')=%s", (month,))
    rows = cur.fetchall()
    conn.close()

    df = pd.DataFrame(rows)
    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

if __name__ == "__main__":
    app.run()