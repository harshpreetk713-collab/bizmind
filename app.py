import os
from flask import Flask, render_template, request, session
import pandas as pd
from io import BytesIO
from werkzeug.utils import secure_filename
import uuid
from azure_storage import upload_to_azure

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bizmind-demo-secret-key")
REQUIRED_COLUMNS = [
    "Date", "Product", "Category",
    "Quantity", "Revenue", "Expenses"
]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    data = session.get("dashboard_data")
    return render_template("dashboard.html", data=data)


@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "GET":
        return render_template("upload.html")

    try:
        file = request.files.get("file")

        if not file or file.filename == "":
            return "Please select a file."

        original_filename = secure_filename(file.filename)
        filename = original_filename.lower()

        if not filename.endswith((".csv", ".xlsx")):
            return "Unsupported file format. Upload CSV or XLSX."

        # Read uploaded file
        file_bytes = file.read()
        file_data = BytesIO(file_bytes)

        # Read CSV or Excel
        if filename.endswith(".csv"):
            df = pd.read_csv(file_data)
        else:
            df = pd.read_excel(file_data)

        if df.empty:
            return "Your uploaded file is empty."

        # Validate columns
        missing = [
            column for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing:
            return "Missing required columns: " + ", ".join(missing)

        df = df[REQUIRED_COLUMNS].copy()

        # Clean numerical data
        for column in ["Quantity", "Revenue", "Expenses"]:
            df[column] = pd.to_numeric(
                df[column], errors="coerce"
            )

        df = df.dropna(
            subset=["Quantity", "Revenue", "Expenses"]
        )

        if df.empty:
            return "No valid business records were found."

        # Clean dates
        df["Date"] = pd.to_datetime(
            df["Date"], errors="coerce"
        )

        df = df.dropna(subset=["Date"])

        if df.empty:
            return "No valid dates were found in your file."

        # Calculate business figures
        total_revenue = float(df["Revenue"].sum())
        total_expenses = float(df["Expenses"].sum())
        total_profit = total_revenue - total_expenses
        total_units = int(df["Quantity"].sum())

        # Monthly revenue
        monthly = (
            df.assign(Month=df["Date"].dt.strftime("%b %Y"))
            .groupby("Month")["Revenue"]
            .sum()
        )

        monthly = monthly.sort_index(
            key=lambda x: pd.to_datetime(x, format="%b %Y")
        )

        # Category revenue
        categories = (
            df.groupby("Category")["Revenue"]
            .sum()
            .sort_values(ascending=False)
        )

        # Recent transactions
        recent = df.sort_values(
            "Date", ascending=False
        ).head(10)

        transactions = []

        for _, row in recent.iterrows():
            transactions.append({
                "product": str(row["Product"]),
                "date": row["Date"].strftime("%b %d, %Y"),
                "revenue": float(row["Revenue"])
            })

        # Upload original file to Azure Blob Storage
        blob_name = f"{uuid.uuid4().hex}_{original_filename}"

        upload_to_azure(file_bytes, blob_name)

        print("File successfully uploaded to Azure!")
        print("Azure container: bizmind-uploads")
        print("Azure blob name:", blob_name)

        # Dashboard data
        dashboard_data = {
            "filename": original_filename,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "total_profit": total_profit,
            "total_units": total_units,
            "total_records": len(df),

            "months": monthly.index.tolist(),
            "monthly_revenue": [
                float(value) for value in monthly.values
            ],

            "categories": categories.index.astype(str).tolist(),
            "category_revenue": [
                float(value) for value in categories.values
            ],

            "transactions": transactions,

            "cloud_storage": "Azure Blob Storage",
            "cloud_status": "Connected",
            "cloud_container": "bizmind-uploads",
            "cloud_filename": blob_name
        }

        session["dashboard_data"] = dashboard_data

        return f"""
        <h1>BizMind - Upload Successful!</h1>

        <p>Your business file has been analysed successfully.</p>

        <p>File: {original_filename}</p>

        <p>Cloud Storage: Azure Blob Storage</p>

        <p>Cloud Upload: Successful</p>

        <p>Total Revenue: ${total_revenue:,.2f}</p>

        <p>Total Expenses: ${total_expenses:,.2f}</p>

        <p>Net Profit: ${total_profit:,.2f}</p>

        <p>Units Sold: {total_units}</p>

        <a href="/dashboard">View Your Dynamic Dashboard</a>
        """

    except Exception as error:
        print("Upload or analysis error:", error)
        return (
            "Unable to process your file. "
            "Please check the application terminal for details."
        )


if __name__ == "__main__":
    app.run(debug=True)
