# 💡 LekaLink Cloud Cost Calculator

The **LekaLink Cloud Cost Calculator** is a Streamlit web app that helps businesses quickly estimate their monthly cloud costs and compare them against LekaLink’s competitive pricing model.  

It generates:
- 📊 A live cost breakdown (VMs, Storage, Bandwidth).  
- 📈 Monthly and percentage savings compared to current spend.  
- 📑 A polished PDF quote that can be downloaded instantly.  
- 📧 Automatic email notifications to the LekaLink sales team for quick follow-up.  

---

## 🌍 Live App
👉 [Use the Calculator](https://lekalinkcalculator.streamlit.app)  

---

## ✨ Features
- **Instant Estimates**: Calculate monthly costs for VMs, storage, and bandwidth.  
- **Savings View**: Compare against current spend with % savings shown.  
- **PDF Export**: Download a professional quote PDF.  
- **Email Integration**: Auto-sends the quote to `sales@lekalink.co.za` (cc: Sarah) via Gmail.  
- **Bitrix24 Webhook Ready**: Captures leads directly into CRM.  

---

## 🛠️ Tech Stack
- [Streamlit](https://streamlit.io) – UI and hosting  
- [Pandas](https://pandas.pydata.org) – data handling  
- [ReportLab](https://www.reportlab.com) – PDF generation  
- [Requests](https://docs.python-requests.org) – Bitrix webhook integration  
- [SMTP](https://docs.python.org/3/library/smtplib.html) – email notifications  

---

## ⚙️ Running Locally

1. Clone the repo:
   ```bash
   git clone https://github.com/Adriennekk/lekalinkcalculator.git
   cd lekalinkcalculator

  
