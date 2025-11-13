
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import database

def run_projection(conn, user_id, projection_end_date_str):
    """
    Generates all missing future transactions based on schedule rules
    up to the projection_end_date.
    """
    schedules = database.get_scheduled_transactions(conn, user_id)
    projection_end_date = datetime.strptime(projection_end_date_str, "%Y-%m-%d").date()
    
    for schedule in schedules:
        schedule_id, _, category_id, description, amount, frequency, start_date_str, end_date_str = schedule[:8]
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
        # Find the last date this was generated, or use the start date
        last_gen_date_str = database.get_last_generated_date(conn, user_id, schedule_id)
        current_date = start_date
        if last_gen_date_str:
            current_date = datetime.strptime(last_gen_date_str, "%Y-%m-%d").date()
        
        # Move to the *next* scheduled date
        if frequency == 'daily':
            current_date += relativedelta(days=1)
        elif frequency == 'weekly':
            current_date += relativedelta(weeks=1)
        elif frequency == 'bi-weekly':
            current_date += relativedelta(weeks=2)
        elif frequency == 'monthly':
            current_date += relativedelta(months=1)
        elif frequency == 'bi-monthly':
            current_date += relativedelta(months=2) # Assuming every 2 months
            
        # Set the loop's end date
        loop_end_date = projection_end_date
        if end_date_str:
            rule_end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if rule_end_date < projection_end_date:
                loop_end_date = rule_end_date

        # Loop and generate missing transactions
        while current_date <= loop_end_date:
            if current_date >= start_date:
                database.add_transaction(
                    conn=conn,
                    user_id=user_id,
                    date=current_date.isoformat(),
                    category_id=category_id,
                    description=description,
                    amount=amount,
                    is_confirmed=0, # 0 = Estimated
                    schedule_id=schedule_id
                )
            
            # Increment to the next date
            if frequency == 'daily':
                current_date += relativedelta(days=1)
            elif frequency == 'weekly':
                current_date += relativedelta(weeks=1)
            elif frequency == 'bi-weekly':
                current_date += relativedelta(weeks=2)
            elif frequency == 'monthly':
                current_date += relativedelta(months=1)
            elif frequency == 'bi-monthly':
                current_date += relativedelta(months=2) # Assuming every 2 months

def get_calendar_data(conn, user_id, view_start_date_str, view_end_date_str):
    """
    Calculates the daily balances, credits, and debits for the calendar view.
    """
    settings = database.get_user_settings(conn, user_id)
    if not settings:
        return pd.DataFrame() # No settings, return empty

    start_balance = settings['start_balance']
    start_date = settings['start_date']

    # 1. Get ALL transactions from the user's global start date
    all_transactions = database.get_all_transactions_after(conn, user_id, start_date)
    
    if not all_transactions:
        # No transactions at all, just return a range of dates with the start balance
        date_range = pd.date_range(start=view_start_date_str, end=view_end_date_str, freq='D')
        df = pd.DataFrame(index=date_range)
        df['balance'] = start_balance
        df['credits'] = 0.0
        df['debits'] = 0.0
        df['is_actual'] = True # No transactions, so the balance is "actual"
        return df.reset_index().rename(columns={'index': 'date'})

    # 2. Convert to DataFrame
    df = pd.DataFrame(all_transactions, columns=[
        'transaction_id', 'user_id', 'schedule_id', 'category_id', 
        'date', 'description', 'amount', 'is_confirmed', 'category_name', 'category_type'
    ])
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'])
    
    # 3. Separate credits and debits
    df['credits'] = df.apply(lambda row: row['amount'] if row['amount'] > 0 else 0, axis=1)
    df['debits'] = df.apply(lambda row: row['amount'] if row['amount'] <= 0 else 0, axis=1)

    # 4. Group by day
    daily_summary = df.groupby(pd.Grouper(key='date', freq='D')).agg(
        credits=('credits', 'sum'),
        debits=('debits', 'sum'),
        is_actual=('is_confirmed', lambda x: (x == 1).all()) # All transactions must be confirmed
    ).reset_index()
    
    daily_summary['net_change'] = daily_summary['credits'] + daily_summary['debits']
    
    # 5. Create a full date range from the user's start date
    full_date_range = pd.date_range(start=start_date, end=view_end_date_str, freq='D')
    calendar_df = pd.DataFrame(index=full_date_range).reset_index().rename(columns={'index': 'date'})
    
    # 6. Merge daily transactions onto the full calendar
    calendar_df = pd.merge(calendar_df, daily_summary, on='date', how='left').fillna(0)
    
    # 7. Calculate the running balance
    calendar_df['balance'] = start_balance + calendar_df['net_change'].cumsum()
    
    # 8. Filter to the user's requested view
    view_start_dt = pd.to_datetime(view_start_date_str)
    view_end_dt = pd.to_datetime(view_end_date_str)
    
    final_df = calendar_df[
        (calendar_df['date'] >= view_start_dt) & 
        (calendar_df['date'] <= view_end_dt)
    ].copy()
    
    final_df['is_actual'] = final_df['is_actual'].astype(bool)
    
    return final_df

print(f"File {REPO_PATH}/engine.py written successfully.")
