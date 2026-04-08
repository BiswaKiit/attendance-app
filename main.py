from flask import Flask, render_template, request

app = Flask(__name__)

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

saved_data = []

def to_int(val):
    return int(val) if val and val.strip() else 0

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        try:
            floor = request.form.get("floor")
            date = request.form.get("date")
            hostel = request.form.get("hostel") or "KP-15"
            floor_strength = to_int(request.form.get("floor_strength"))

            year_data = {}
            total_year_strength = 0

            valid = True

            for year in years:
                strength = to_int(request.form.get(f"{year}_strength"))
                present = to_int(request.form.get(f"{year}_present"))
                leave = to_int(request.form.get(f"{year}_leave"))
                absent = to_int(request.form.get(f"{year}_absent"))

                # Year validation
                if (present + leave + absent) != strength:
                    valid = False

                total_year_strength += strength

                year_data[year] = {
                    "Strength": strength,
                    "Present": present,
                    "Leave": leave,
                    "Absent": absent
                }

            # Floor validation
            if total_year_strength != floor_strength:
                valid = False

            if not valid:
                message = "❌ Data mismatch! Please check values."
            else:
                saved_data.append({
                    "date": date,
                    "hostel": hostel,
                    "floor": floor,
                    "floor_strength": floor_strength,
                    "year_data": year_data
                })
                message = "✅ Data Saved Successfully!"

        except Exception as e:
            message = f"Error: {str(e)}"

    return render_template("index.html", floors=floors, years=years, message=message)


@app.route("/report", methods=["POST"])
def report():
    report_type = request.form.get("report_type")

    total_strength = 0
    total_present = 0
    total_leave = 0

    year_summary = {y: {"Strength":0, "Present":0, "Leave":0} for y in years}

    for d in saved_data:
        total_strength += d["floor_strength"]

        for y, val in d["year_data"].items():
            year_summary[y]["Strength"] += val["Strength"]
            year_summary[y]["Present"] += val["Present"]
            year_summary[y]["Leave"] += val["Leave"] + val["Absent"]

            total_present += val["Present"]
            total_leave += val["Leave"] + val["Absent"]

    return render_template("report.html",
                           data=saved_data,
                           report_type=report_type,
                           total_strength=total_strength,
                           total_present=total_present,
                           total_leave=total_leave,
                           year_summary=year_summary)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)