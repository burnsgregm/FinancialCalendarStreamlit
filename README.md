
# Streamlit Financial Calendar (PoC)

This is a proof-of-concept web application for a calendar-based financial tracker, built with Streamlit and Python. It is a secure, multi-user application secured by Google OAuth.

The primary goal of this app is to provide a visual, at-a-glance calendar to see a projected financial balance on any given future day.



## 🚀 Live Demo

A live version of this app is deployed on Streamlit Community Cloud.

**Note:** This is a secure, multi-user application.
1.  You will be required to **log in with a Google account**.
2.  Your data is **100% private** to your account. You will be given a fresh, empty calendar.
3.  Your data is ephemeral and will be reset when the app server restarts.

## ✨ Core Features

* **Google Authentication:** The entire app is secured behind Streamlit's built-in Google OAuth.
* **Multi-Tenant Database:** Each user's data is siloed. A recruiter logging in will see a clean, empty app, while the owner will see their private financial data.
* **Dynamic Calendar View:** A main calendar (Monthly, Weekly, Daily) that displays:
    * **Projected End-of-Day Balance**
    * Total Daily Credits
    * Total Daily Debits
* **Actual vs. Estimated:** Balances are **bold** if all of that day's transactions are "Confirmed" and *italicized* if any are "Estimated."
* **Transaction Management:**
    * Click any day to open a pop-up and view all transactions.
    * Add new one-time transactions.
    * Delete transactions.
* **Projection Engine (The "Brain"):**
    * Add **scheduled, recurring transactions** (e.g., "Paycheck" every 2 weeks, "Rent" every month).
    * The app auto-generates all future estimated transactions based on these rules.
* **Category & Settings Management:**
    * Users can manage their own list of credit/debit categories.
    * Users can set their global "Starting Balance" and "Start Date."

## 🛠️ How It Was Built

This application was built using a "Colab Factory" notebook—a single, reproducible Google Colab file that:
1.  Installs all dependencies.
2.  Writes the complete Python code for the `database.py` module (handles all SQLite logic).
3.  Writes the complete Python code for the `engine.py` module (handles all financial projection logic).
4.  Writes the main Streamlit `Home.py` app file.
5.  Commits and pushes the entire application to this GitHub repository.

### Tech Stack
* **Frontend:** Streamlit
* **Backend:** Python
* **Database:** SQLite (for multi-user data-siloing)
* **Core Libraries:** Pandas, python-dateutil, streamlit-calendar
* **Authentication:** Streamlit Community Cloud (Google OAuth)
