import streamlit as st
import pandas as pd
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# File Path for Excel Storage
EXCEL_FILE = "billing_data.xlsx"

# Load or Create Excel File
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=["Receipt No.", "Customer Name", "College", "Phone No.", "Project Title", "Reference", "Date", "Total Cost",
                               "1st Payment Date", "1st Payment Amount", "1st Payment Method",
                               "2nd Payment Date", "2nd Payment Amount", "2nd Payment Method",
                               "3rd Payment Date", "3rd Payment Amount", "3rd Payment Method",
                               "Deduction Amount", "Total Paid", "Balance"])
    df.to_excel(EXCEL_FILE, index=False)
else:
    df = pd.read_excel(EXCEL_FILE)

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
        new_entry = pd.DataFrame([[receipt_no, customer_name, college, phone_no, project_title, reference, date, total_cost, None, None, None, None, None, None, None, None, None, 0, 0, total_cost]],
                                 columns=df.columns)
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
        st.success("✅ Bill Saved Successfully!")

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
                    idx = df[df["Receipt No."].astype(str) == receipt_no].index[0]
                    df.at[idx, "Deduction Amount"] += deduction_amount
                    df.at[idx, "Balance"] = df.at[idx, "Total Cost"] - df.at[idx, "Total Paid"] - df.at[idx, "Deduction Amount"]
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success("✅ Deduction Updated Successfully!")
            else:
                payment_date = st.date_input("Payment Date")
                payment_amount = st.number_input("Enter Payment Amount ($)", min_value=0.0, format="%.2f")
                payment_method = st.radio("Select Payment Method:", ["GPay", "Cash"])
                
                if st.button("Update Payment"):
                    idx = df[df["Receipt No."].astype(str) == receipt_no].index[0]

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

                    # Ensure all payment values are not None
                    payment_1 = df.at[idx, "1st Payment Amount"] if pd.notna(df.at[idx, "1st Payment Amount"]) else 0.0
                    payment_2 = df.at[idx, "2nd Payment Amount"] if pd.notna(df.at[idx, "2nd Payment Amount"]) else 0.0
                    payment_3 = df.at[idx, "3rd Payment Amount"] if pd.notna(df.at[idx, "3rd Payment Amount"]) else 0.0
                    deduction = df.at[idx, "Deduction Amount"] if pd.notna(df.at[idx, "Deduction Amount"]) else 0.0

                    # Calculate Total Paid
                    total_paid = payment_1 + payment_2 + payment_3
                    df.at[idx, "Total Paid"] = total_paid

                    # Calculate Balance
                    df.at[idx, "Balance"] = df.at[idx, "Total Cost"] - total_paid - deduction

                    df.to_excel(EXCEL_FILE, index=False)
                    st.success("✅ Payment Updated Successfully!")


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
            
            # Border
            border_canvas = canvas.Canvas(buffer, pagesize=letter)
            border_canvas.setStrokeColor(colors.black)
            border_canvas.rect(20, 20, 550, 750, stroke=1, fill=0)
            border_canvas.showPage()
            border_canvas.save()
            
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
            payment_summary = [
                ["Total Cost:", f"${receipt_data['Total Cost']:.2f}"],
                ["1st Payment:", f"${receipt_data['1st Payment Amount']:.2f} ({receipt_data['1st Payment Method']})"],
                ["2nd Payment:", f"${receipt_data['2nd Payment Amount']:.2f} ({receipt_data['2nd Payment Method']})"],
                ["3rd Payment:", f"${receipt_data['3rd Payment Amount']:.2f} ({receipt_data['3rd Payment Method']})"],
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
            
            # Terms & Conditions
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

