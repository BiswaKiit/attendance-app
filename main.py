from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import json
import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

DATA_FILE = "data.json"

ATTENDANTS = ["Sunam", "Rabi Narayan", "Nrushingha", "Satya", "Alok", "Sarat", "Subasish"]

# ---------- LOAD / SAVE ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------- HOME ----------
@app.route("/")
def index():
    return render_template("index.html", attendants=ATTENDANTS)

# ---------- SAVE ----------
@app.route("/save", methods=["POST"])
def save():
    data = load_data()

    date = request.form.get("date")

    floors = ["Ground", "1st", "2nd", "3rd"]
    years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

    entry = {}

    for floor in floors:
        entry[floor] = {
            "attendant": request.form.get(f"{floor}_attendant"),
            "strength": int(request.form.get(f"{floor}_strength") or 0),
            "years": {}
        }

        floor_total = 0

        for year in years:
            s = int(request.form.get(f"{floor}_{year}_strength") or 0)
            p = int(request.form.get(f"{floor}_{year}_present") or 0)
            l = int(request.form.get(f"{floor}_{year}_leave") or 0)
            a = int(request.form.get(f"{floor}_{year}_absent") or 0)

            # validation
            if s != p + l + a:
                return f"Error: {floor} - {year} mismatch"

            floor_total += s

            entry[floor]["years"][year] = {
                "Strength": s,
                "Present": p,
                "Leave": l,
                "Absent": a
            }

        if floor_total != entry[floor]["strength"]:
            return f"Error: {floor} total mismatch"

    data[date] = entry
    save_data(data)

    return redirect(url_for("index"))

# ---------- REPORT ----------
@app.route("/report", methods=["POST"])
def report():
    data = load_data()

    date = request.form.get("date")
    report_type = request.form.get("report_type")

    if date not in data:
        return "No data found"

    entry = data[date]

    total_strength = total_present = total_leave = total_absent = 0

    full_data = {}

    for floor, fdata in entry.items():
        floor_totals = {"Strength":0,"Present":0,"Leave":0,"Absent":0}
        years = {}

        for year, y in fdata["years"].items():
            years[year] = y

            floor_totals["Strength"] += y["Strength"]
            floor_totals["Present"] += y["Present"]
            floor_totals["Leave"] += y["Leave"]
            floor_totals["Absent"] += y["Absent"]

        full_data[floor] = {
            "years": years,
            "totals": floor_totals,
            "attendant": fdata["attendant"]
        }

        total_strength += floor_totals["Strength"]
        total_present += floor_totals["Present"]
        total_leave += floor_totals["Leave"]
        total_absent += floor_totals["Absent"]

    return render_template(
        "report.html",
        report_type=report_type,
        data=full_data,
        total_strength=total_strength,
        total_present=total_present,
        total_leave=total_leave + total_absent,
        date=date
    )

# ---------- SHARE ----------
@app.route("/share/<date>")
def share(date):
    data = load_data()

    if date not in data:
        return "No data"

    entry = data[date]

    total_s = total_p = total_l = total_a = 0

    for floor in entry.values():
        for y in floor["years"].values():
            total_s += y["Strength"]
            total_p += y["Present"]
            total_l += y["Leave"]
            total_a += y["Absent"]

    text = f"""
KING PALACE - 15

Date: {date}

Total Strength: {total_s}
Total Present: {total_p}
Total Leave: {total_l + total_a}
"""

    return jsonify({"text": text})

# ---------- PDF ----------
@app.route("/download/<date>")
def download(date):
    data = load_data()

    if date not in data:
        return "No data"

    entry = data[date]

    filename = f"report_{date}.pdf"
    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("KING PALACE - 15", styles["Title"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Date: {date}", styles["Normal"]))

    total_s = total_p = total_l = total_a = 0

    for floor, fdata in entry.items():
        content.append(Spacer(1, 10))
        content.append(Paragraph(f"{floor} Floor ({fdata['attendant']})", styles["Heading2"]))

        for year, y in fdata["years"].items():
            line = f"{year} → S:{y['Strength']} P:{y['Present']} L:{y['Leave']} A:{y['Absent']}"
            content.append(Paragraph(line, styles["Normal"]))

            total_s += y["Strength"]
            total_p += y["Present"]
            total_l += y["Leave"]
            total_a += y["Absent"]

    content.append(Spacer(1, 10))
    content.append(Paragraph("Grand Total", styles["Heading2"]))
    content.append(Paragraph(f"S:{total_s} P:{total_p} L:{total_l + total_a}", styles["Normal"]))

    doc.build(content)

    response = make_response(open(filename, "rb").read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    return response

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)