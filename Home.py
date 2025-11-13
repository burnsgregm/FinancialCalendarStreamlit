
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar
import time

# Import our custom backend modules
import database
import engine

# --- 1. PAGE CONFIG & APP TITLE ---
APP_TITLE = "Future-Balance Financial Calendar (PoC)"
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. AUTHENTICATION & USER SETUP ---
# This is the "front door" of the app.
# It checks if the user is logged in via Streamlit's Google OAuth.
try:
    # st.user.email is automatically populated by Streamlit Cloud
    # when the app is set to "Private"
    user_email = st.user.email
except AttributeError:
    # This happens in local dev, so we'll use a placeholder.
    # On Streamlit Cloud, this 'except' block will not be hit.
    user_email = "local_dev_user@example.com"
except Exception as e:
    st.error("Authentication failed. Please log in to continue.")
    # You can host this image on imgur or in your GitHub repo
    # st.image("https://i.imgur.com/39SST9b.png", use_column_width=True)
    st.stop()

# --- Initialize Database & User ---
# We use the user's email as their unique ID.
# This ensures all data is siloed.
try:
    conn = database.initialize_database()
    USER_ID = database.get_or_create_user(conn, user_email)
except Exception as e:
    st.error(f"Error initializing database: {e}")
    st.stop()

# --- 3. STATE MANAGEMENT ---
# Initialize session state variables
if "selected_day" not in st.session_state:
    st.session_state.selected_day = None
    
if "calendar_view_start" not in st.session_state:
    st.session_state.calendar_view_start = datetime.today().date().replace(day=1).isoformat()
    
if "calendar_view_end" not in st.session_state:
    # Calculate end of the month
    today = datetime.today().date()
    next_month = today.replace(day=28) + timedelta(days=4)
    end_of_month = next_month - timedelta(days=next_month.day)
    st.session_state.calendar_view_end = end_of_month.isoformat()

# --- 4. HELPER FUNCTIONS ---

def format_currency(value):
    """Formats a float as $USD currency."""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"

def format_calendar_item(row):
    """
    Formats the DataFrame row into the dictionary structure
    required by the streamlit-calendar component.
    """
    balance = row['balance']
    credits = row['credits']
    debits = row['debits']
    is_actual = row['is_actual']
    
    # Set title: Bold if actual, Italic if estimated
    title_style = "font-weight: 600;" if is_actual else "font-style: italic;"
    # Set color: Red if negative, black if positive
    color = "#D32F2F" if balance < 0 else "#000000" # Red for negative
    
    # Create the multi-line calendar entry using HTML
    title_html = f"""
    <div style='{title_style} color: {color}; font-size: 1.1em;'>{format_currency(balance)}</div>
    <div style='font-size: 0.9em; color: #1E88E5;'>+{format_currency(credits)}</div>
    <div style='font-size: 0.9em; color: #D32F2F;'>{format_currency(debits)}</div>
    """
    
    return {
        "title": title_html,
        "start": row['date'].isoformat(),
        "end": row['date'].isoformat(),
        "allDay": True,
        "editable": False,
        "extendedProps": {
            "balance": balance,
            "credits": credits,
            "debits": debits,
            "is_actual": is_actual,
        }
    }

# --- 5. DATA LOADING & PROJECTION ---
# This is the core logic that runs on every interaction
try:
    # 1. Run the projection engine to create future transactions
    # We'll project 2 years into the future
    projection_end_date = (datetime.today() + relativedelta(years=2)).isoformat()
    engine.run_projection(conn, USER_ID, projection_end_date)
    
    # 2. Get the calculated data for the calendar's current view
    calendar_df = engine.get_calendar_data(
        conn,
        USER_ID,
        st.session_state.calendar_view_start,
        st.session_state.calendar_view_end
    )
    
    if calendar_df.empty:
        calendar_items = []
    else:
        # 3. Format the data for the calendar component
        calendar_items = calendar_df.apply(format_calendar_item, axis=1).tolist()
        
except Exception as e:
    st.error(f"Error running financial engine: {e}")
    st.stop()


# --- 6. MAIN PAGE UI ---
st.title(APP_TITLE)
st.markdown(f"Welcome, **{user_email}**. This calendar shows your projected daily balance.")

# --- Calendar Legend ---
with st.container():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<span style='font-weight: 600;'>{format_currency(123.45)}</span>: **Actual** Balance", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<span style='font-style: italic;'>{format_currency(123.45)}</span>: *Estimated* Balance", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<span style='color: #1E88E5;'>+{format_currency(123.45)}</span>: Total Credits", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<span style='color: #D32F2F;'>{format_currency(-123.45)}</span>: Total Debits", unsafe_allow_html=True)

# --- The Calendar Component ---
calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay"
    },
    "initialDate": datetime.today().isoformat(),
    "initialView": "dayGridMonth",
    "selectable": True,
    "editable": False,
    "dayMaxEvents": True, # Allows scrolling for many events
    "eventContent": {
        "html": True # IMPORTANT: Allows us to use custom HTML for the title
    }
}

cal = calendar(
    events=calendar_items,
    options=calendar_options,
    callbacks=["dateClick", "datesSet"], # datesSet is for month navigation
    key="financial_calendar"
)

# --- Handle Calendar Callbacks ---
# *** THIS IS THE FIX ***
# We split the ISO datetime string at the 'T' to get just the date
if cal and cal.get('callback') == 'dateClick':
    date_str = cal.get('dateClick')['date'].split('T')[0]
    st.session_state.selected_day = date_str
    st.rerun()

if cal and cal.get('callback') == 'datesSet':
    start_str = cal.get('datesSet')['start'].split('T')[0]
    end_str = cal.get('datesSet')['end'].split('T')[0]
    st.session_state.calendar_view_start = start_str
    st.session_state.calendar_view_end = end_str
    st.rerun()


# --- 7. "DAY VIEW" DIALOG (Pop-up) ---
if st.session_state.selected_day:
    @st.dialog("Day View", on_dismiss=lambda: st.session_state.pop("selected_day", None))
    def day_view_dialog():
        day_str = st.session_state.selected_day
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        
        # Get data for the selected day
        day_row = calendar_df[calendar_df['date'].dt.date == day]
        
        if day_row.empty:
            st.error("Could not find data for this day.")
            return

        day_data = day_row.iloc[0]
        
        st.header(f"Details for {day.strftime('%A, %B %d, %Y')}")
        
        # Display the day's summary
        col1, col2, col3 = st.columns(3)
        balance_style = "font-weight: 600;" if day_data['is_actual'] else "font-style: italic;"
        balance_color = "#D32F2F" if day_data['balance'] < 0 else "#000000"
        
        col1.markdown(f"**Balance:** <span style='{balance_style} color: {balance_color}; font-size: 1.2em;'>{format_currency(day_data['balance'])}</span>", unsafe_allow_html=True)
        col2.metric("Total Credits", format_currency(day_data['credits']))
        col3.metric("Total Debits", format_currency(day_data['debits']))
        
        st.divider()
        
        # Display transactions for the day
        st.subheader("Transactions")
        transactions = database.get_transactions_for_day(conn, USER_ID, day_str)
        
        if not transactions:
            st.write("No transactions for this day.")
        else:
            for tx in transactions:
                tx_id, _, _, cat_id, _, desc, amt, confirmed, cat_name, cat_type = tx
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    # Description and Category
                    desc_str = desc or "N/A"
                    cat_str = f" ({cat_name})" if cat_name else ""
                    col1.write(f"**{desc_str}**{cat_str}")
                    
                    # Amount and Status
                    color = "#1E88E5" if amt > 0 else "#D32F2F"
                    status = "✅ Confirmed" if confirmed else "⌛ Estimated"
                    col2.markdown(f"<span style='color: {color}; font-weight: 600;'>{format_currency(amt)}</span>  |  {status}", unsafe_allow_html=True)

                    # Delete Button
                    if col3.button("Delete", key=f"del_{tx_id}", use_container_width=True):
                        database.delete_transaction(conn, tx_id, USER_ID)
                        st.session_state.pop("selected_day", None) # Close dialog
                        st.rerun()
        
        # --- Add New Transaction Button ---
        st.divider()
        if st.button("Add New Transaction...", use_container_width=True):
            st.session_state.add_tx_date = day # Pre-fill date
            st.session_state.pop("selected_day", None) # Close this dialog
            st.rerun()

    day_view_dialog()

# --- 8. "ADD NEW TRANSACTION" DIALOG (Pop-up) ---
if "add_tx_date" in st.session_state:
    @st.dialog("Add New Transaction")
    def add_transaction_dialog():
        prefill_date = st.session_state.add_tx_date
        
        st.header("Add New Transaction")
        
        # Load categories for the dropdown
        categories = database.get_categories(conn, USER_ID)
        cat_options = {c[0]: f"{c[1]} ({c[2]})" for c in categories}
        cat_ids = list(cat_options.keys())
        
        with st.form(key="add_tx_form"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date", value=prefill_date)
                description = st.text_input("Description (e.g., 'Paycheck', 'Netflix')")
                try:
                    category_id = st.selectbox("Category", 
                                            options=cat_ids, 
                                            format_func=lambda x: cat_options.get(x, "None"))
                except st.errors.StreamlitAPIException:
                     # This handles the case where the category list is empty
                     category_id = None
                     st.write("No categories found. Add one in the sidebar.")
            
            with col2:
                amount_str = st.text_input("Amount (use '-' for debits, e.g., -50.25)")
                is_confirmed = st.checkbox("Confirmed (Actual Amount)", value=True)
            
            is_scheduled = st.toggle("Schedule this as a recurring transaction?", value=False)
            
            frequency = None
            end_date = None
            if is_scheduled:
                st.write("Scheduling Options")
                col3, col4 = st.columns(2)
                with col3:
                    frequency = st.selectbox("Frequency", 
                                             ['daily', 'weekly', 'bi-weekly', 'monthly', 'bi-monthly'])
                with col4:
                    end_date = st.date_input("End Date (Optional)", value=None)
            
            # Form submission
            submitted = st.form_submit_button("Save Transaction", use_container_width=True)
            if submitted:
                try:
                    amount = float(amount_str)
                except (ValueError, TypeError):
                    st.error("Amount must be a number (e.g., 50.25 or -14.99)")
                    return
                
                try:
                    if is_scheduled:
                        # Save as a NEW scheduled transaction rule
                        database.add_scheduled_transaction(
                            conn, USER_ID, category_id, description, amount, 
                            frequency, date.isoformat(), end_date.isoformat() if end_date else None
                        )
                        st.success("Scheduled transaction saved! The calendar will update.")
                    else:
                        # Save as a single, one-time transaction
                        database.add_transaction(
                            conn, USER_ID, date.isoformat(), category_id, 
                            description, amount, 1 if is_confirmed else 0
                        )
                        st.success("Transaction saved!")
                    
                    # Clear state and close dialog
                    st.session_state.pop("add_tx_date", None)
                    time.sleep(1) # Give user time to read success message
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to save: {e}")

    add_transaction_dialog()

# --- 9. SIDEBAR: Settings & Category Management ---
with st.sidebar:
    st.header("Settings")
    
    # --- User Settings Form ---
    st.subheader("Account Setup")
    settings = database.get_user_settings(conn, USER_ID)
    with st.form("settings_form"):
        st.write("Set your starting balance and date.")
        start_date = st.date_input("Start Date", 
                                   value=datetime.strptime(settings['start_date'], "%Y-%m-%d").date())
        start_balance = st.number_input("Starting Balance", 
                                        value=settings['start_balance'],
                                        format="%.2f")
        
        if st.form_submit_button("Save Settings"):
            database.update_user_settings(conn, USER_ID, start_balance, start_date.isoformat())
            st.success("Settings saved!")
            st.rerun()
            
    # --- Category Manager ---
    st.divider()
    st.subheader("Manage Categories")
    
    categories = database.get_categories(conn, USER_ID)
    if categories:
        for cat in categories:
            cat_id, _, name, type = cat
            col1, col2 = st.columns([3, 1])
            col1.write(f"{name} ({type})")
            if col2.button("X", key=f"del_cat_{cat_id}", help=f"Delete {name}"):
                try:
                    database.delete_category(conn, cat_id, USER_ID)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete. This category is in use by a scheduled transaction. Error: {e}")
    
    with st.form("add_category_form", clear_on_submit=True):
        st.write("Add New Category")
        new_cat_name = st.text_input("Name", placeholder="e.g., 'Gas'")
        new_cat_type = st.selectbox("Type", ['debit', 'credit'])
        
        if st.form_submit_button("Add Category"):
            if new_cat_name:
                database.add_category(conn, USER_ID, new_cat_name, new_cat_type)
                st.rerun()
            else:
                st.error("Category name cannot be empty.")
