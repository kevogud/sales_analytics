import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from hashlib import sha256
import datetime

# Initialize database
def get_db_connection():
    conn = sqlite3.connect('appp.db')
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        approved BOOLEAN NOT NULL DEFAULT 0,
                        store_id INTEGER,
                        FOREIGN KEY(store_id) REFERENCES stores(id)
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL
                    )''')
    # Create an admin user
    admin_username = "admin"
    admin_password = hash_password("admin123")  # Admin password is 'admin123'
    try:
        cursor.execute("INSERT INTO users (username, password, approved) VALUES (?, ?, 1)", (admin_username, admin_password))
    except sqlite3.IntegrityError:
        # Admin user already exists
        pass

    # Insert predefined stores if they don't exist
    store_values = [121, 201, 4305, 6709, 7510]
    for store in store_values:
        try:
            cursor.execute("INSERT INTO stores (id, name) VALUES (?, ?)", (store, f"Store {store}"))
        except sqlite3.IntegrityError:
            # Store already exists
            pass

    conn.commit()
    conn.close()

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def admin_page():
    st.title("Admin Page")

    # Admin login
    if 'admin_logged_in' not in st.session_state or not st.session_state['admin_logged_in']:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password = ? AND store_id IS NULL", (username, hash_password(password)))
            admin_user = cursor.fetchone()
            
            if admin_user:
                st.session_state['admin_logged_in'] = True
                st.success("Logged in as Admin")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials or not an admin")
            conn.close()
    else:
        manage_users()
        #manage_stores()
        if st.button("Logout"):
            st.session_state['admin_logged_in'] = False
            st.experimental_rerun()

def manage_users():
    st.subheader("Manage Users")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE approved = 0")
    pending_users = cursor.fetchall()
    
    if pending_users:
        for user in pending_users:
            #st.write(f"User ID: {user[0]}, Username: {user[1]}")
            if st.button(f"Approve {user[1]}", key=f"approve_{user[0]}"):
                cursor.execute("UPDATE users SET approved = 1 WHERE id = ?", (user[0],))
                conn.commit()
                st.success(f"User {user[1]} approved")
    else:
        st.write("No pending users")
    
    cursor.execute("SELECT * FROM users WHERE approved = 1 AND store_id IS NULL")
    approved_users = cursor.fetchall()
    
    # Predefined store values
    store_values = ['121', '201', '4305', '6709', '7510']
    
    for user in approved_users[1:]:
        st.write(f"User ID: {user[0]}, Username: {user[1]}")
        store_id = st.selectbox(f"Assign Store to {user[1]}", store_values, key=f"assign_{user[0]}")
        if st.button(f"Assign Store", key=f"assign_btn_{user[0]}"):
            cursor.execute("UPDATE users SET store_id = ? WHERE id = ?", (store_id, user[0]))
            conn.commit()
            st.success(f"Store assigned to {user[1]}")
    
    conn.close()

def manage_stores():
    st.subheader("Manage Stores")
    store_name = st.text_input("Store Name")
    
    if st.button("Add Store"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO stores (name) VALUES (?)", (store_name,))
        conn.commit()
        conn.close()
        st.success(f"Store {store_name} added")

def user_page():
    st.title("User Page")

    if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
        choice = st.selectbox("Choose an option", ["Sign Up", "Login"])

        if choice == "Sign Up":
            username = st.text_input("Choose a Username")
            password = st.text_input("Choose a Password", type="password")
            
            if st.button("Sign Up"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
                    conn.commit()
                    st.success("Sign Up successful, please wait for admin approval")
                except sqlite3.IntegrityError:
                    st.error("Username already taken")
                conn.close()

        elif choice == "Login":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
                user = cursor.fetchone()
                
                if user and user[3]:
                    st.session_state['user_logged_in'] = True
                    st.session_state['user_id'] = user[0]
                    st.session_state['store_id'] = user[4]
                    st.success("Logged in as User")
                    st.experimental_rerun()
                elif user:
                    st.warning("Waiting for admin approval")
                else:
                    st.error("Invalid credentials")
                conn.close()
    else:
        user_id = st.session_state['user_id']
        store_id = st.session_state['store_id']
        
        if store_id:
            st.success(f"Assigned to store ID {store_id}")
            user_upload(store_id)
        else:
            st.warning("Waiting for store assignment by admin")
        
        if st.button("Logout"):
            st.session_state['user_logged_in'] = False
            st.experimental_rerun()

def user_upload(store_id):
    st.subheader("Upload Sales Data")
    uploaded_file = st.file_uploader("Upload Excel file", type="xlsx")
    
    if uploaded_file:
        data = load_data(uploaded_file)
        data = preprocess_data(data)
        filtered_data = filter_by_store(data, store_id)
        if st.button("Analyze Data"):
            st.write("Data uploaded successfully, now you can view analytics")
            st.session_state['filtered_data'] = filtered_data

def analytics_page():
    st.title("Analytics Page")
    
    if 'filtered_data' in st.session_state:
        data = st.session_state['filtered_data']
        
        st.write(data.describe())
        
        start_date = st.date_input("Start Date", value=datetime.date(2023, 6, 1))
        end_date = st.date_input("End Date", value=datetime.date(2023, 6, 30))
        filtered_df = filter_by_date(data, start_date, end_date)
        
        if filtered_df.empty:
            st.warning("No data available for the selected date range.")
            return
        
        total_sales = calculate_total_sales(filtered_df)
        st.metric("Total Sales", f"${total_sales:,.2f}")
        
        sales_location = sales_by_location(filtered_df)
        st.write("Sales by Location")
        st.bar_chart(sales_location.set_index('Store'))
        
        sales_department = sales_by_department(filtered_df)
        st.write("Sales by Department")
        st.bar_chart(sales_department.set_index('Department'))
        
        highest_sales_item, lowest_sales_item = highest_lowest_sales_items(filtered_df)
        if highest_sales_item is not None:
            st.write("Highest Sales Item")
            st.table(highest_sales_item)
        else:
            st.write("No data available for highest sales item.")
        
        if lowest_sales_item is not None:
            st.write("Lowest Sales Item")
            st.table(lowest_sales_item)
        else:
            st.write("No data available for lowest sales item.")
        
        highest_qty_item = highest_sold_item_by_quantity(filtered_df)
        if highest_qty_item is not None:
            st.write("Highest Sold Item by Quantity")
            st.table(highest_qty_item)
        else:
            st.write("No data available for highest sold item by quantity.")
        
        most_profitable = most_profitable_item(filtered_df)
        if most_profitable is not None:
            st.write("Most Profitable Item")
            st.table(most_profitable)
        else:
            st.write("No data available for most profitable item.")
        
        sales_variation = sales_variation_across_locations(filtered_df)
        st.write("Sales Variation Across Locations")
        st.dataframe(sales_variation)
    else:
        st.warning("Please upload data in the User Page and get it approved by admin to view analytics")

# Data processing functions
def load_data(file_path):
    data = pd.read_excel(file_path, skiprows=4)
    column_names = [
        'Store', 'Date', 'Scan Code', 'Description', 'Department', 'Qty', 
        'POS Cost', 'POS Retail', 'Retail at Sale', 'Selling Units', 
        'Margin', 'Profit', 'Promo ID', 'Tran ID', 'Register'
    ]
    data.columns = column_names
    data = data.drop(data.index[0])
    data.reset_index(drop=True, inplace=True)
    data['Scan Code'].fillna('Unknown', inplace=True)
    data['Retail at Sale'].fillna(data['POS Retail'], inplace=True)
    data['Date'] = pd.to_datetime(data['Date'])
    return data

def remove_outliers_iqr(df, column):
    Q1 = df[column].quantile(0.10)
    Q3 = df[column].quantile(0.90)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

def preprocess_data(data):
    numeric_cols = ["Qty", "POS Cost", "POS Retail", "Retail at Sale", "Selling Units", "Margin", "Profit"]
    for col in numeric_cols:
        data = remove_outliers_iqr(data, col)
    return data

def filter_by_store(data, store_id):
    return data[data['Store'] == store_id]

# Function to filter data by date range
def filter_by_date(df, start_date, end_date):
    mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
    return df.loc[mask]

# Function to calculate total sales
def calculate_total_sales(df):
    return df['Retail at Sale'].sum()

# Function to calculate sales by location
def sales_by_location(df):
    return df.groupby('Store')['Retail at Sale'].sum().reset_index()

# Function to calculate sales by department
def sales_by_department(df):
    return df.groupby('Department')['Retail at Sale'].sum().reset_index()

# Function to find the highest and lowest sales items
def highest_lowest_sales_items(df):
    sales_items = df.groupby('Description')['Retail at Sale'].sum().reset_index()
    highest_sales_item = sales_items.loc[sales_items['Retail at Sale'].idxmax()]
    lowest_sales_item = sales_items.loc[sales_items['Retail at Sale'].idxmin()]
    return highest_sales_item, lowest_sales_item

# Function to find the highest sold item by quantity
def highest_sold_item_by_quantity(df):
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce')  
    qty_items = df.groupby('Description')['Qty'].sum().reset_index()
    highest_qty_item = qty_items.loc[qty_items['Qty'].idxmax()]
    return highest_qty_item

# Function to find the most profitable item
def most_profitable_item(df):
    df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce')  
    profit_items = df.groupby('Description')['Profit'].sum().reset_index()
    most_profitable = profit_items.loc[profit_items['Profit'].idxmax()]
    return most_profitable

# Function to calculate sales variation across locations
def sales_variation_across_locations(df):
    variation = df.groupby(['Store', 'Description'])['Qty'].sum().unstack().fillna(0)
    return variation

# Main
init_db()
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Admin", "User", "Analytics"])

if page == "Admin":
    admin_page()
elif page == "User":
    user_page()
elif page == "Analytics":
    analytics_page()
