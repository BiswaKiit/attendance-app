from flask import Flask, render_template, request, redirect

app = Flask(__name__)

floors = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

# Temporary storage (later we can move to database)
saved_data = []

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        floor = request.form.get("floor")
        date = request.form.get("date")
        hostel = request.form.get("hostel", "KP-15")
        floor_strength = int(request.form.get("floor_strength", 0))

        total_present = 0
        total_leave = 0
        total_absent = 0

        year_data = {}

        for year in years:
            present = int(request.form.get(f"{year}_present", 0))
            leave = int(request.form.get(f"{year}_leave", 0))
            absent = int(request.form.get(f"{year}_absent", 0))

            total_present += present
            total_leave += leave
            total_absent += absent

            year_data[year] = {
                "Present": present,
                "Leave": leave,
                "Absent": absent
            }

        # ✅ VALIDATION
        if (total_present + total_leave + total_absent) != floor_strength:
            message = "❌ Total mismatch! Please check values."
        else:
            saved_data.append({
                "date": date,
                "hostel": hostel,
                "floor": floor,
                "floor_strength": floor_strength,
                "year_data": year_data
            })
            message = "✅ Data Saved Successfully!"

    return render_template("index.html", floors=floors, years=years, message=message)


@app.route("/report", methods=["GET", "POST"])
def report():
    report_type = request.form.get("report_type")
    month = request.form.get("month")

    filtered = []

    for d in saved_data:
        if month:
            if d["date"].startswith(month):
                filtered.append(d)
        else:
            filtered.append(d)

    return render_template("report.html", data=filtered, report_type=report_type)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)