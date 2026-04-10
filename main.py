from flask import Flask, render_template, request, redirect
import pandas as pd
import os

app = Flask(__name__)

DATA_FILE = "data.csv"

# Create file if not exists
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Date", "Present", "Absent", "Vacant"])
    df.to_csv(DATA_FILE, index=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/save", methods=["POST"])
def save():
    try:
        date = request.form.get("date")
        present = int(request.form.get("present", 0))
        absent = int(request.form.get("absent", 0))
        vacant = int(request.form.get("vacant", 0))

        new_data = pd.DataFrame([[date, present, absent, vacant]],
                                columns=["Date", "Present", "Absent", "Vacant"])

        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        return redirect("/")
    except Exception as e:
        return f"Error saving data: {str(e)}"


@app.route("/report", methods=["GET", "POST"])
def report():
    try:
        df = pd.read_csv(DATA_FILE)

        report_type = request.form.get("type", "full")
        selected_date = request.form.get("date")
        selected_month = request.form.get("month")

        # Convert Date column
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        # FILTERING
        if selected_date:
            df = df[df["Date"] == pd.to_datetime(selected_date)]

        if selected_month:
            df = df[df["Date"].dt.strftime("%Y-%m") == selected_month]

        # SUMMARY CALCULATION
        total_present = df["Present"].sum()
        total_absent = df["Absent"].sum()
        total_vacant = df["Vacant"].sum()

        return render_template(
            "report.html",
            data=df.to_dict(orient="records"),
            total_present=total_present,
            total_absent=total_absent,
            total_vacant=total_vacant,
            report_type=report_type
        )

    except Exception as e:
        return f"Error generating report: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)