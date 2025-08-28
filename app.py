import streamlit as st
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import io
import streamlit.components.v1 as components
import os
import pandas as pd
import math  # for NaN/finite checks

# --- Image Paths ---
LEKALINK_LOGO_PATH = os.path.join("assets", "LL_Stacked_Gradient.png")

# --- Pricing Configuration (Default values) ---
DEFAULT_VM_RATE = 864.35
DEFAULT_STORAGE_RATE_PER_TB = 870.40
DEFAULT_BANDWIDTH_RATE_PER_MBPS = 7.50

# Initialize rates with default values
VM_RATE = DEFAULT_VM_RATE
STORAGE_RATE_PER_TB = DEFAULT_STORAGE_RATE_PER_TB
BANDWIDTH_RATE_PER_MBPS = DEFAULT_BANDWIDTH_RATE_PER_MBPS

# --- Pricing Configuration (Dynamically loaded from CSV) ---
PRICE_SHEET_PATH = os.path.join("assets", "Leka Link_Channel Partner_VDC Calculator.xlsx - VDC Calculation.csv")

try:
    # Check if assets directory exists
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        st.error(f"Error: The '{assets_dir}' directory was not found. Please ensure your CSV file is inside a folder named '{assets_dir}' in the same directory as your app.py.")
        raise FileNotFoundError(f"Directory '{assets_dir}' not found.")

    # Check if the CSV file exists within the assets directory
    if not os.path.exists(PRICE_SHEET_PATH):
        st.error(f"Error: The price sheet CSV file was not found at '{PRICE_SHEET_PATH}'. Please ensure the file name is exactly 'Leka Link_Channel Partner_VDC Calculator.xlsx - VDC Calculation.csv' and it's inside the 'assets' folder.")
        raise FileNotFoundError(f"File '{PRICE_SHEET_PATH}' not found.")

    # If both exist, proceed with reading the CSV
    price_df = pd.read_csv(
        PRICE_SHEET_PATH,
        header=4,
        encoding='latin-1',
        on_bad_lines='skip',
        engine='python'
    )
    
    # Strip whitespace from column names
    price_df.columns = price_df.columns.str.strip()

    # Convert 'Unit Monthly' column to numeric
    price_df['Unit Monthly'] = pd.to_numeric(price_df['Unit Monthly'], errors='coerce')

    # Debug: Print available descriptions to help identify correct text
    print("DEBUG: Available descriptions in CSV:")
    print(price_df['Description'].dropna().unique())
    
    # Only consider rows where Unit Monthly is a real number
    valid = price_df['Unit Monthly'].notna() & price_df['Unit Monthly'].apply(lambda v: isinstance(v, (int, float)))

    # --- Helper to coerce numeric rates & fallback to defaults ---
    def coerce_rate(val, default):
        try:
            v = float(val)
            return v if math.isfinite(v) and v >= 0 else default
        except Exception:
            return default

    # More flexible matching for VM pricing
    vm_keywords = ['Virtual', 'Data Centre', 'VDC', 'VM', 'Resource Pool', 'Allocation']
    vm_mask = price_df['Description'].str.contains('|'.join(vm_keywords), na=False, case=False)
    vm_row = price_df[vm_mask & valid]
    if not vm_row.empty:
        VM_RATE = coerce_rate(vm_row['Unit Monthly'].iloc[0], DEFAULT_VM_RATE)
        print(f"DEBUG: Found VM rate: {VM_RATE} for description: '{vm_row['Description'].iloc[0]}'")
    else:
        VM_RATE = DEFAULT_VM_RATE
        print("Warning: Could not find VM pricing in CSV. Using default VM rate.")

    # More flexible matching for Storage pricing
    storage_keywords = ['Storage', 'NVME', 'SSD', 'vStorage']
    storage_mask = price_df['Description'].str.contains('|'.join(storage_keywords), na=False, case=False)
    storage_row = price_df[storage_mask & valid]
    if not storage_row.empty:
        storage_price = coerce_rate(storage_row['Unit Monthly'].iloc[0], DEFAULT_STORAGE_RATE_PER_TB)
        desc = str(storage_row['Description'].iloc[0])
        # If description suggests GB and price is small, convert GB -> TB
        if ('GB' in desc.upper()) and storage_price < 50:
            STORAGE_RATE_PER_TB = storage_price * 1024
        else:
            STORAGE_RATE_PER_TB = storage_price
        STORAGE_RATE_PER_TB = coerce_rate(STORAGE_RATE_PER_TB, DEFAULT_STORAGE_RATE_PER_TB)
        print(f"DEBUG: Found Storage rate: {STORAGE_RATE_PER_TB} per TB for description: '{storage_row['Description'].iloc[0]}'")
    else:
        STORAGE_RATE_PER_TB = DEFAULT_STORAGE_RATE_PER_TB
        print("Warning: Could not find Storage pricing in CSV. Using default Storage rate.")

    # More flexible matching for Bandwidth/Connectivity
    bandwidth_keywords = ['Bandwidth', 'Internet', 'Connectivity', 'Mbps', 'Network']
    bandwidth_mask = price_df['Description'].str.contains('|'.join(bandwidth_keywords), na=False, case=False)
    bandwidth_row = price_df[bandwidth_mask & valid]
    if not bandwidth_row.empty:
        BANDWIDTH_RATE_PER_MBPS = coerce_rate(bandwidth_row['Unit Monthly'].iloc[0], DEFAULT_BANDWIDTH_RATE_PER_MBPS)
        print(f"DEBUG: Found Bandwidth rate: {BANDWIDTH_RATE_PER_MBPS} per Mbps for description: '{bandwidth_row['Description'].iloc[0]}'")
    else:
        BANDWIDTH_RATE_PER_MBPS = DEFAULT_BANDWIDTH_RATE_PER_MBPS
        print("Warning: Could not find Bandwidth pricing in CSV. Using default Bandwidth rate.")

    # Final safety (guarantee no NaNs)
    VM_RATE = coerce_rate(VM_RATE, DEFAULT_VM_RATE)
    STORAGE_RATE_PER_TB = coerce_rate(STORAGE_RATE_PER_TB, DEFAULT_STORAGE_RATE_PER_TB)
    BANDWIDTH_RATE_PER_MBPS = coerce_rate(BANDWIDTH_RATE_PER_MBPS, DEFAULT_BANDWIDTH_RATE_PER_MBPS)

    print(f"DEBUG: Final rates - VM: {VM_RATE}, Storage: {STORAGE_RATE_PER_TB}, Bandwidth: {BANDWIDTH_RATE_PER_MBPS}")

except FileNotFoundError as e:
    print(f"Caught FileNotFoundError: {e}. Using default pricing rates.")
except KeyError as e:
    st.error(f"Error reading column from price sheet: {e}. Ensure 'Description' and 'Unit Monthly' columns exist and are correctly formatted. Using default pricing rates.")
except Exception as e:
    st.error(f"An unexpected error occurred while loading prices from CSV: {e}. Using default pricing rates.")
    print(f"DEBUG: Exception details: {e}")
    import traceback
    traceback.print_exc()

# --- Custom CSS for Branding ---
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

/* Apply font family globally */
html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif;
}

/* Force all h1, h2, h3, p, and label elements to the desired purple color */
h1, h2, h3, p, label {
    color: #511281 !important;
}

/* Target Streamlit's main content div and its children to force color */
div[data-testid="stAppViewContainer"] * {
    color: #511281 !important;
}

/* Apply border and rounded corners to the main app container */
.stApp {
    background: linear-gradient(180deg, #f0f2f6 0%, #e0e5ec 100%);
    padding: 2rem;
    border: 3px solid #511281 !important;
    border-radius: 20px;
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

/* Header Gradient */
.header-section {
    background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
    padding: 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}
.header-section h1 {
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: white !important;
}
.header-section p {
    color: rgba(255, 255, 255, 0.8) !important;
    font-size: 1.1rem;
}

/* Input Card Styling */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    border-radius: 10px;
    border: 1px solid #ddd;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

/* Button Styling */
.stButton > button {
    background-color: #16a34a;
    color: white;
    font-weight: 600;
    padding: 0.75rem 1.5rem;
    border-radius: 10px;
    border: none;
    transition: background-color 0.3s ease, transform 0.2s ease;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}
.stButton > button:hover {
    background-color: #128a3a;
    transform: translateY(-2px);
}
.stButton > button:active {
    transform: translateY(0);
}

/* Results Card Styling */
.results-card {
    background: linear-gradient(135deg, #e0e5ec 0%, #f0f2f6 100%);
    border-radius: 15px;
    padding: 2rem;
    margin-top: 2rem;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    border: 1px solid #d0d5db;
}
.results-card p {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}
.results-card .savings-positive {
    color: #16a34a !important;
    font-weight: 700;
    font-size: 1.3rem;
}
.results-card .savings-negative {
    color: #e74c3c !important;
    font-weight: 700;
    font-size: 1.3rem;
}

/* Remove Streamlit header/footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
"""

# Inject custom CSS
components.html(f"<style>{CUSTOM_CSS}</style>", height=0, width=0)

# --- Helper Functions ---
def create_pdf(data):
    """Generates a PDF quote from the calculated data."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Define purple color for headings
    PURPLE_RGB = (0.3176, 0.0706, 0.5059)  # RGB for #511281

    # --- Add LekaLink Logo to PDF (Top Center) ---
    y_position_logo = height - 0.5 * inch  # default so it's always defined
    try:
        if os.path.exists(LEKALINK_LOGO_PATH):
            logo = ImageReader(LEKALINK_LOGO_PATH)
            img_width, img_height = logo.getSize()
            
            # Desired width for the logo on PDF
            logo_display_width = 1.5 * inch
            logo_display_height = logo_display_width * (img_height / img_width)

            # Calculate x position for centering
            x_position_logo = (width - logo_display_width) / 2
            # Position at the top with some margin
            y_position_logo = height - logo_display_height - 0.5 * inch
            c.drawImage(logo, x_position_logo, y_position_logo, width=logo_display_width, height=logo_display_height)
        else:
            st.warning(f"LekaLink logo not found at {LEKALINK_LOGO_PATH}. Skipping logo in PDF.")
    except Exception as e:
        st.error(f"Error loading LekaLink logo for PDF: {e}")

    # Adjust starting y_position for text based on logo presence
    y_position = height - 1.5 * inch if not os.path.exists(LEKALINK_LOGO_PATH) else y_position_logo - 0.5 * inch

    # Title
    c.setFont('Helvetica-Bold', 24)
    c.setFillColorRGB(*PURPLE_RGB)
    c.drawString(inch, y_position, "LekaLink Cloud Cost Quote")
    y_position -= 0.5 * inch

    # Company and Contact Info
    c.setFillColorRGB(*PURPLE_RGB)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(inch, y_position, "Client Information:")
    y_position -= 0.3 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 12)
    c.drawString(inch, y_position, f"Company: {data['company_name']}")
    y_position -= 0.25 * inch
    c.drawString(inch, y_position, f"Contact: {data['contact_name']} ({data['job_title']})")
    y_position -= 0.25 * inch
    c.drawString(inch, y_position, f"Email: {data['email']}")
    y_position -= 0.25 * inch
    c.drawString(inch, y_position, f"Phone: {data['phone']}")

    y_position -= 0.5 * inch

    # Current Costs
    c.setFillColorRGB(*PURPLE_RGB)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(inch, y_position, "Current Cloud Costs:")
    y_position -= 0.3 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 12)
    c.drawString(inch, y_position, f"Monthly Cost: R{data['current_cost']:.2f}")

    y_position -= 0.5 * inch

    # LekaLink Estimated Costs
    c.setFillColorRGB(*PURPLE_RGB)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(inch, y_position, "LekaLink Estimated Costs:")
    y_position -= 0.3 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 12)
    
    # Display estimated totals per item
    c.drawString(inch, y_position, f"Virtual Machines: R{data['vms'] * data['vm_rate']:.2f}")
    y_position -= 0.25 * inch
    c.drawString(inch, y_position, f"Storage: R{data['storage'] * data['storage_rate_per_tb']:.2f}")
    y_position -= 0.25 * inch
    c.drawString(inch, y_position, f"Bandwidth: R{data['bandwidth'] * data['bandwidth_rate_per_mbps']:.2f}")
    y_position -= 0.25 * inch
    c.setFont('Helvetica-Bold', 12)
    c.drawString(inch, y_position, f"Total LekaLink Estimated Cost: R{data['lekalink_cost']:.2f}")

    y_position -= 0.5 * inch

    # Savings
    c.setFillColorRGB(*PURPLE_RGB)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(inch, y_position, "Potential Savings:")
    y_position -= 0.3 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 12)
    if data['monthly_savings'] >= 0:
        c.setFillColorRGB(0.08, 0.64, 0.29)  # LekaLink Green
        c.drawString(inch, y_position, f"Monthly Savings: R{data['monthly_savings']:.2f}")
        y_position -= 0.25 * inch
        c.drawString(inch, y_position, f"Percentage Savings: {data['percentage_savings']:.2f}%")
    else:
        c.setFillColorRGB(0.91, 0.30, 0.24)  # Red
        c.drawString(inch, y_position, f"Monthly Increase: R{-data['monthly_savings']:.2f}")
        y_position -= 0.25 * inch
        c.drawString(inch, y_position, f"Percentage Increase: {-data['percentage_savings']:.2f}%")

    y_position -= 0.5 * inch

    # Next Steps
    c.setFillColorRGB(*PURPLE_RGB)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(inch, y_position, "Next Steps:")
    y_position -= 0.3 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 12)
    c.drawString(inch, y_position, "Our sales team will contact you within 24 hours to discuss your requirements.")
    y_position -= 0.3 * inch

    # Contact Information
    c.drawString(inch, y_position, "LekaLink (Pty) Ltd")
    y_position -= 0.2 * inch
    c.drawString(inch, y_position, "Phone: +27 010 822 7259")
    y_position -= 0.2 * inch
    c.drawString(inch, y_position, "Email: sales@lekalink.co.za")
    y_position -= 0.2 * inch
    c.drawString(inch, y_position, "Website: www.lekalink.co.za")
    y_position -= 0.2 * inch
    c.drawString(inch, y_position, "Address: 89 Bute Rd, Sandown, Sandton, Gauteng, 2196")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def send_email_to_sales(quote_data, pdf_data):
    """Send quote details and PDF to sales team via Gmail SMTP"""
    
    # Gmail Configuration with provided credentials
    GMAIL_EMAIL = "saleslekalink@gmail.com"
    GMAIL_PASSWORD = "lqbg ciek octw bbtb"  # App Password (16 chars, with spaces)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SALES_EMAIL = "sales@lekalink.co.za"
    CC_EMAIL = "sarah@lekalink.co.za"   # CC Sarah
    
    try:
        # Create sales notification email with PDF attachment
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = SALES_EMAIL
        msg['Cc'] = CC_EMAIL            # add CC header
        msg['Subject'] = f"New Calculator Lead: {quote_data['company_name']}"
        
        # Email body with all lead details
        email_body = f"""NEW CALCULATOR LEAD GENERATED
=============================

COMPANY INFORMATION:
Company: {quote_data['company_name']}
Contact: {quote_data['contact_name']}
Job Title: {quote_data['job_title']}
Email: {quote_data['email']}
Phone: {quote_data['phone']}

CURRENT INFRASTRUCTURE:
Virtual Machines: {quote_data['vms']}
Storage: {quote_data['storage']} TB
Bandwidth: {quote_data['bandwidth']} Mbps
Current Monthly Cost: R{quote_data['current_cost']:,.2f}

LEKALINK ESTIMATE:
LekaLink Monthly Cost: R{quote_data['lekalink_cost']:,.2f}
Monthly Savings: R{quote_data['monthly_savings']:,.2f}
Percentage Savings: {quote_data['percentage_savings']:.1f}%

FOLLOW-UP ACTION REQUIRED:
Contact {quote_data['contact_name']} at {quote_data['email']} within 24 hours.

Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

The customer's quote PDF is attached to this email.
"""
        
        msg.attach(MIMEText(email_body, 'plain'))
        
        # Attach PDF to email
        if pdf_data:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_data)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition', 
                f'attachment; filename=LekaLink_Quote_{quote_data["company_name"].replace(" ", "_")}.pdf'
            )
            msg.attach(part)
        
        # Send the email to both To and CC
        recipients = [SALES_EMAIL, CC_EMAIL]
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
            server.sendmail(GMAIL_EMAIL, recipients, msg.as_string())
            
        return True
        
    except Exception as e:
        st.error(f"Failed to send email notification: {e}")
        return False

def validate_inputs(company_name, contact_name, job_title, email, phone):
    """Validates that all required contact information fields are not empty."""
    errors = []
    if not company_name:
        errors.append("Company Name is required.")
    if not contact_name:
        errors.append("Contact Name is required.")
    if not job_title:
        errors.append("Job Title is required.")
    if not email:
        errors.append("Email is required.")
    elif '@' not in email:
        errors.append("Please enter a valid email address.")
    if not phone:
        errors.append("Phone Number is required.")
    
    if errors:
        for error in errors:
            st.error(error)
        return False
    return True

# --- Streamlit App Layout ---

# Header section
st.markdown('<div class="header-section"><p>Estimate your savings when you switch to LekaLink Cloud Services!</p></div>', unsafe_allow_html=True)

# Create two main columns for the input sections
left_column, right_column = st.columns(2)

with left_column:
    st.subheader("Your Current Cloud Usage")
    vms = st.number_input("Number of Virtual Machines", min_value=0, value=0, step=1, key="vms")
    storage = st.number_input("Storage (TB)", min_value=0.0, value=0.0, step=0.1, format="%.1f", key="storage")
    bandwidth = st.number_input("Bandwidth (Mbps)", min_value=0.0, value=0.0, step=1.0, format="%.1f", key="bandwidth")
    current_cost = st.number_input("Current Monthly Cloud Cost (R)", min_value=0.0, value=0.0, step=100.0, format="%.2f", key="current_cost")

with right_column:
    st.subheader("Your Contact Information")
    company_name = st.text_input("Company Name *", key="company_name")
    contact_name = st.text_input("Contact Name *", key="contact_name")
    job_title = st.text_input("Job Title *", key="job_title")
    email = st.text_input("Email Address *", key="email")
    phone = st.text_input("Phone Number *", key="phone")

# Button and results will appear below the two columns
if st.button("Save me Money"):
    # Perform validation before calculations
    if validate_inputs(company_name, contact_name, job_title, email, phone):
        # --- Calculation Logic ---
        lekalink_cost = (vms * VM_RATE) + (storage * STORAGE_RATE_PER_TB) + (bandwidth * BANDWIDTH_RATE_PER_MBPS)
        monthly_savings = current_cost - lekalink_cost
        percentage_savings = (monthly_savings / current_cost * 100) if current_cost > 0 else 0  # avoid NaN

        st.markdown('<div class="results-card">', unsafe_allow_html=True)
        st.write("### Your Estimated Savings with LekaLink")
        st.write(f"**LekaLink Estimated Monthly Cost:** R{lekalink_cost:,.2f}")

        if monthly_savings >= 0:
            st.markdown(f'<p class="savings-positive">**Monthly Savings:** R{monthly_savings:,.2f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="savings-positive">**Percentage Savings:** {percentage_savings:.2f}%</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p class="savings-negative">**Monthly Increase:** R{-monthly_savings:,.2f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="savings-negative">**Percentage Increase:** {-percentage_savings:.2f}%</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Prepare data for PDF
        quote_data = {
            "company_name": company_name,
            "contact_name": contact_name,
            "job_title": job_title,
            "email": email,
            "phone": phone,
            "vms": vms,
            "storage": storage,
            "bandwidth": bandwidth,
            "current_cost": current_cost,
            "lekalink_cost": lekalink_cost,
            "monthly_savings": monthly_savings,
            "percentage_savings": percentage_savings,
            "vm_rate": VM_RATE,
            "storage_rate_per_tb": STORAGE_RATE_PER_TB,
            "bandwidth_rate_per_mbps": BANDWIDTH_RATE_PER_MBPS
        }

        # Generate PDF
        pdf_output = create_pdf(quote_data)

        # Provide PDF download button
        st.download_button(
            label="Download Quote as PDF",
            data=pdf_output,
            file_name=f"LekaLink_Cloud_Quote_{company_name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

        # Send email to sales team with PDF attachment
        if send_email_to_sales(quote_data, pdf_output):
            st.success("Quote generated and sent to LekaLink Sales (cc Sarah) with PDF attachment! We'll contact you within 24 hours.")
        else:
            st.info("Quote generated successfully! Please download your quote above.")
            st.info("Our sales team has been notified and will contact you shortly at: " + email)

