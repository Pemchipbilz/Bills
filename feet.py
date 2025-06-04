import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import gspread
from google.oauth2.service_account import Credentials

# ✅ 1. Path to your service account JSON file
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Make sure this file is in your working directory

# ✅ 2. Your actual Google Sheet ID
SPREADSHEET_ID = '1RXaCzBWbjGtFNEc963e6k6l7r1Ee6U4iK5ih5Syzp7U'  # This is your shared Google Sheet ID

# ✅ 3. Define scope for Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ 4. Authorize and create gspread client using google-auth
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# ✅ 5. Open your Google Sheet by key
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Use .worksheet("Sheet1") if needed



# Columns expected in your sheet (same as your DataFrame columns)
COLUMNS = [
    "Receipt No.", "Customer Name", "College", "Phone No.", "Project Title", "Reference", "Date", "Total Cost",
    "1st Payment Date", "1st Payment Amount", "1st Payment Method",
    "2nd Payment Date", "2nd Payment Amount", "2nd Payment Method",
    "3rd Payment Date", "3rd Payment Amount", "3rd Payment Method",
    "Deduction Amount", "Total Paid", "Balance"
]

# Helper to read all data from Google Sheet into DataFrame
def load_data():
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records, columns=COLUMNS)
        # Convert dates from string to datetime if needed
        for date_col in ["Date", "1st Payment Date", "2nd Payment Date", "3rd Payment Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
        # Convert numeric columns and fill NaNs
        for col in ["Total Cost", "1st Payment Amount", "2nd Payment Amount", "3rd Payment Amount", "Deduction Amount", "Total Paid", "Balance"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets: {e}")
        return pd.DataFrame(columns=COLUMNS)

# Helper to save DataFrame back to Google Sheets (overwrite all data)
def save_data(df):
    try:
        # Prepare data as list of lists including header
        df_to_save = df.copy()
        # Format dates as string
        for date_col in ["Date", "1st Payment Date", "2nd Payment Date", "3rd Payment Date"]:
            if date_col in df_to_save.columns:
                df_to_save[date_col] = df_to_save[date_col].astype(str)
        data = [COLUMNS] + df_to_save.fillna("").values.tolist()
        sheet.clear()
        sheet.update(data)
        return True, None
    except Exception as e:
        return False, str(e)

# Load data on app start
df = load_data()

st.title("🧾 Billing Application")

menu = st.sidebar.selectbox("Select Action", ["New Entry", "Update Payment", "Download Receipt"])

if menu == "New Entry":
    st.header("Enter New Billing Details")
    
    col1, col2 = st.columns(2)
    with col1:
        receipt_no = st.text_input("Receipt No.")
        customer_name = st.text_input("Customer Name")
        phone_no = st.text_input("Phone No.")
        project_title = st.text_input("Project Title")
        college = st.text_input("College Name")
    
    with col2:
        reference = st.text_input("Reference")
        date = st.date_input("Date")
        total_cost = st.number_input("Total Cost ($)", min_value=0.0, format="%.2f")
    
    if st.button("Save Bill"):
        if receipt_no.strip() == "":
            st.error("Receipt No. cannot be empty!")
        elif receipt_no in df["Receipt No."].astype(str).values:
            st.error("Receipt No. already exists!")
        else:
            new_entry = {
                "Receipt No.": receipt_no,
                "Customer Name": customer_name,
                "College": college,
                "Phone No.": phone_no,
                "Project Title": project_title,
                "Reference": reference,
                "Date": date,
                "Total Cost": total_cost,
                "1st Payment Date": None,
                "1st Payment Amount": 0,
                "1st Payment Method": None,
                "2nd Payment Date": None,
                "2nd Payment Amount": 0,
                "2nd Payment Method": None,
                "3rd Payment Date": None,
                "3rd Payment Amount": 0,
                "3rd Payment Method": None,
                "Deduction Amount": 0,
                "Total Paid": 0,
                "Balance": total_cost
            }
            df = df.append(new_entry, ignore_index=True)
            success, error = save_data(df)
            if success:
                st.success("✅ Bill Saved Successfully!")
            else:
                st.error(f"❌ Failed to save bill: {error}")

elif menu == "Update Payment":
    st.header("Update Payment Details")
    
    receipt_no = st.text_input("Enter Receipt No. to Update Payment")
    
    if receipt_no:
        filtered_df = df[df["Receipt No."].astype(str) == receipt_no]
        if filtered_df.empty:
            st.error("No records found for this Receipt No.")
        else:
            st.write("### Existing Billing Details")
            st.dataframe(filtered_df)
            
            payment_stage = st.selectbox("Select Update Stage", ["1st Payment", "2nd Payment", "3rd Payment", "Deduction Update"])
            
            if payment_stage == "Deduction Update":
                deduction_amount = st.number_input("Enter Deduction Amount ($)", min_value=0.0, format="%.2f")
                
                if st.button("Update Deduction"):
                    idx = df.index[df["Receipt No."].astype(str) == receipt_no][0]
                    current_deduction = df.at[idx, "Deduction Amount"] or 0
                    df.at[idx, "Deduction Amount"] = current_deduction + deduction_amount
                    total_paid = df.at[idx, "Total Paid"] or 0
                    total_cost = df.at[idx, "Total Cost"]
                    df.at[idx, "Balance"] = total_cost - total_paid - df.at[idx, "Deduction Amount"]
                    success, error = save_data(df)
                    if success:
                        st.success("✅ Deduction Updated Successfully!")
                    else:
                        st.error(f"❌ Failed to update deduction: {error}")
            else:
                payment_date = st.date_input("Payment Date")
                payment_amount = st.number_input("Enter Payment Amount ($)", min_value=0.0, format="%.2f")
                payment_method = st.radio("Select Payment Method:", ["GPay", "Cash"])
                
                if st.button("Update Payment"):
                    idx = df.index[df["Receipt No."].astype(str) == receipt_no][0]

                    if payment_stage == "1st Payment":
                        df.at[idx, "1st Payment Date"] = payment_date
                        df.at[idx, "1st Payment Amount"] = payment_amount
                        df.at[idx, "1st Payment Method"] = payment_method
                    elif payment_stage == "2nd Payment":
                        df.at[idx, "2nd Payment Date"] = payment_date
                        df.at[idx, "2nd Payment Amount"] = payment_amount
                        df.at[idx, "2nd Payment Method"] = payment_method
                    elif payment_stage == "3rd Payment":
                        df.at[idx, "3rd Payment Date"] = payment_date
                        df.at[idx, "3rd Payment Amount"] = payment_amount
                        df.at[idx, "3rd Payment Method"] = payment_method

                    payment_1 = df.at[idx, "1st Payment Amount"] or 0.0
                    payment_2 = df.at[idx, "2nd Payment Amount"] or 0.0
                    payment_3 = df.at[idx, "3rd Payment Amount"] or 0.0
                    deduction = df.at[idx, "Deduction Amount"] or 0.0

                    total_paid = payment_1 + payment_2 + payment_3
                    df.at[idx, "Total Paid"] = total_paid

                    df.at[idx, "Balance"] = df.at[idx, "Total Cost"] - total_paid - deduction

                    success, error = save_data(df)
                    if success:
                        st.success("✅ Payment Updated Successfully!")
                    else:
                        st.error(f"❌ Failed to update payment: {error}")

elif menu == "Download Receipt":
    st.header("Download Receipt")
    receipt_no = st.text_input("Enter Receipt No. to Download Receipt")
    
    terms_image = st.file_uploader("Upload Terms & Conditions Image", type=["jpg", "png"])  
    
    if receipt_no:
        filtered_df = df[df["Receipt No."].astype(str) == receipt_no]
        if filtered_df.empty:
            st.error("No records found for this Receipt No.")
        else:
            receipt_data = filtered_df.iloc[0]
            buffer = BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            # Header
            elements.append(Paragraph("<b>RECEIPT</b>", styles['Title']))
            elements.append(Spacer(1, 12))
            
            # Company Info
            company_info = [
                ["Pemchip Infotech"],
                ["10, Vaibhav Nagar Phase 3, Siva Shakthi Complex, Near VIT, Katpadi, Vellore"],
                ["Contact: 9361286811 / 9626914437 / 8148983811"],
                ["Email: pemchipinfotech@gmail.com | Website: pemchip.com"]
            ]
            table = Table(company_info)
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER')
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
            
            # Customer Details
            customer_details = [
                ["Receipt No:", receipt_data["Receipt No."]],
                ["Customer Name:", receipt_data["Customer Name"]],
                ["College:", receipt_data["College"]],
                ["Phone No:", receipt_data["Phone No."]],
                ["Project Title:", receipt_data["Project Title"]],
                ["Date:", str(receipt_data["Date"])]
            ]
            table = Table(customer_details, colWidths=[150, 300])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
            
            # Payment Summary
            def format_payment(amount, method):
                if pd.isna(amount) or amount == 0 or pd.isna(method):
                    return "$0.00"
                return f"${amount:.2f} ({method})"
            
            payment_summary = [
                ["Total Cost:", f"${receipt_data['Total Cost']:.2f}"],
                ["1st Payment:", format_payment(receipt_data['1st Payment Amount'], receipt_data['1st Payment Method'])],
                ["2nd Payment:", format_payment(receipt_data['2nd Payment Amount'], receipt_data['2nd Payment Method'])],
                ["3rd Payment:", format_payment(receipt_data['3rd Payment Amount'], receipt_data['3rd Payment Method'])],
                ["Total Paid:", f"${receipt_data['Total Paid']:.2f}"],
                ["Balance:", f"${receipt_data['Balance']:.2f}"],
                ["Deduction Amount:", f"${receipt_data['Deduction Amount']:.2f}"]
            ]
            table = Table(payment_summary, colWidths=[150, 300])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
            
            # Terms & Conditions Image
            if terms_image:
                img = Image(terms_image, width=400, height=200)
                elements.append(img)
            
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("<b>Thank You for Your Business!</b>", styles['Normal']))
            elements.append(Paragraph("Pemchip Infotech", styles['Normal']))
            elements.append(Paragraph("<b>Terms & Conditions:</b>", styles['Normal']))

            # Fixed multi-line terms and conditions text
            terms_text = (
                "1. The initial deposit amount is non-refundable.<br/>"
                "2. Software projects require a minimum of 10 days, and hardware projects require a minimum of 15 days for completion.<br/>"
                "3. A 50% payment is required at the start of the project for hardware projects.<br/>"
                "4. Payments will be made according to project milestones. For example, if 30% of the project is completed, "
                    "30% of the total payment is due at that stage.<br/>"
                "5. No project work will be delivered if there is any outstanding payment.<br/>"
                "6. Once the project is delivered, any requested changes will be charged according to the scope of work involved.<br/>"
                "7. The project will be delivered strictly according to the requirements specified in the registration form in advance, "
                    "and no additional features or scope will be included unless specified and agreed upon in advance.<br/>"
                "8. If a client refers a friend, they will receive a referral discount on their own project."
            )
            elements.append(Paragraph(terms_text, styles['Normal']))
            
            pdf.build(elements)
            buffer.seek(0)
            st.download_button("Download Receipt PDF", buffer, file_name=f"receipt_{receipt_no}.pdf", mime="application/pdf")
