from flask import Flask, render_template, request

app = Flask(__name__)

floors = ["Ground", "1st", "2nd", "3rd", "4th"]
years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = {}
        summary_year = {year: {"Strength": 0, "Present": 0, "Leave": 0} for year in years}

        hostel = request.form.get("hostel")
        date = request.form.get("date")

        total_strength = 0
        total_present = 0
        total_leave = 0

        for floor in floors:
            data[floor] = {}

            for year in years:
                strength = int(request.form.get(f"{floor}_{year}_strength", 0))
                present = int(request.form.get(f"{floor}_{year}_present", 0))
                leave = int(request.form.get(f"{floor}_{year}_leave", 0))
                absent = int(request.form.get(f"{floor}_{year}_absent", 0))

                total_l = leave + absent

                data[floor][year] = {
                    "Strength": strength,
                    "Present": present,
                    "Leave": leave,
                    "Absent": absent
                }

                # Summary Year-wise
                summary_year[year]["Strength"] += strength
                summary_year[year]["Present"] += present
                summary_year[year]["Leave"] += total_l

                # Overall totals
                total_strength += strength
                total_present += present
                total_leave += total_l

        return render_template(
            "report.html",
            data=data,
            summary_year=summary_year,
            total_strength=total_strength,
            total_present=total_present,
            total_leave=total_leave,
            hostel=hostel,
            date=date
        )

    return render_template("index.html", floors=floors, years=years)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)