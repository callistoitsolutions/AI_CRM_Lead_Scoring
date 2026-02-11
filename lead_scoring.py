"""
Lead Scoring Model for Rental CRM Leads - Streamlit App WITH ADMIN/USER LOGIN
Identical to your AI PPT generator system
"""
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import hashlib
import json
from datetime import datetime
import matplotlib.pyplot as plt
# ... (your existing imports for sklearn, xgboost, etc.)

# === LOGIN SYSTEM (EXACT COPY FROM AI PPT) ===
def init_database():
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        role TEXT DEFAULT 'user'
    )''')
    
    # Sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        logout_time TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        session_token TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Usage logs
    c.execute('''CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        filename TEXT,
        records_processed INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Create admin if not exists
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
                  ('admin', admin_password, 'admin@leadscoring.com', 'admin'))
        conn.commit()
    
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute("SELECT id, username, role, is_active FROM users WHERE username=? AND password_hash=?",
                  (username, password_hash))
        user = c.fetchone()
        if user and user[3]:  # is_active
            c.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user[0]))
            # Clear old sessions
            try:
                c.execute("UPDATE sessions SET is_active=0, logout_time=? WHERE user_id=? AND is_active=1",
                          (datetime.now(), user[0]))
            except sqlite3.OperationalError:
                pass
            session_token = hashlib.md5(f"{user[0]}{datetime.now()}".encode()).hexdigest()
            try:
                c.execute("INSERT INTO sessions (user_id, login_time, is_active, session_token) VALUES (?, ?, ?, ?)",
                          (user[0], datetime.now(), 1, session_token))
            except sqlite3.OperationalError:
                c.execute("INSERT INTO sessions (user_id, login_time) VALUES (?, ?)", (user[0], datetime.now()))
            conn.commit()
            conn.close()
            return user[0], user[1], user[2], session_token
    except:
        pass
    conn.close()
    return None

def logout_user(user_id):
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE sessions SET is_active=0, logout_time=? WHERE user_id=? AND is_active=1",
                  (datetime.now(), user_id))
    except:
        pass
    conn.commit()
    conn.close()

def log_usage(user_id, action, filename, records=0):
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO usage_logs (user_id, action, filename, records_processed) VALUES (?, ?, ?, ?)",
              (user_id, action, filename, records))
    conn.commit()
    conn.close()

# Admin functions (same as AI PPT)
def get_user_stats(user_id):
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usage_logs WHERE user_id=? AND action='score'", (user_id,))
    total_analyses = c.fetchone()[0]
    c.execute("SELECT SUM(records_processed) FROM usage_logs WHERE user_id=? AND action='score'", (user_id,))
    total_records = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,))
    total_logins = c.fetchone()[0]
    conn.close()
    return total_analyses, total_records, total_logins

def get_all_users():
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT id, username, email, created_at, last_login, is_active, role FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    return users

def toggle_user_status(user_id, is_active):
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET is_active=? WHERE id=?", (is_active, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def get_currently_loggedin_users():
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("""SELECT u.id, u.username, u.email, s.login_time, u.role 
                     FROM sessions s JOIN users u ON s.user_id = u.id 
                     WHERE s.is_active = 1 ORDER BY s.login_time DESC""")
        active_users = c.fetchall()
    except:
        active_users = []
    conn.close()
    return active_users

def get_system_stats():
    conn = sqlite3.connect('leadscoring.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role='user'")
    total_users = c.fetchone()[0]
    try:
        c.execute("SELECT COUNT(*) FROM sessions WHERE is_active=1")
        currently_online = c.fetchone()[0]
    except:
        currently_online = 0
    c.execute("SELECT COUNT(*) FROM usage_logs WHERE action='score'")
    total_analyses = c.fetchone()[0]
    c.execute("SELECT SUM(records_processed) FROM usage_logs WHERE action='score'")
    total_records = c.fetchone()[0] or 0
    conn.close()
    return total_users, currently_online, total_analyses, total_records

# Your existing feature engineering, model training functions (unchanged)
def create_features(df):
    # ... (your exact code)
    pass

# ... (all your other functions: create_target_variable, get_feature_importance, main model logic)

def show_login_page():
    st.markdown("""
    <style>
    .login-container {max-width: 400px; margin: 100px auto; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    .login-header {text-align: center; color: #1f77b4; margin-bottom: 30px;}
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-header">Lead Scoring System</h1>', unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Login", use_container_width=True, type="primary"):
                if username and password:
                    user = verify_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        log_usage(user[0], 'login', 'N/A')
                        st.success(f"Welcome, {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Enter username & password")
        with col_btn2:
            if st.button("Demo", use_container_width=True):
                st.info("**Admin:** admin / admin123")
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Lead Scoring System", layout="wide")
    init_database()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.logged_in:
        show_login_page()
        st.stop()
    
    # === DASHBOARD (Admin vs User) ===
    st.markdown("""
    <style>
    .main-header {font-size: 2.8rem; font-weight: 800; background: linear-gradient(120deg, #1f77b4, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 0.5rem;}
    .user-info {background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;}
    .online-indicator {display: inline-block; width: 10px; height: 10px; background: #4caf50; border-radius: 50%; margin-right: 5px; animation: pulse 2s infinite;}
    @keyframes pulse {0%, 100% {opacity: 1;} 50% {opacity: 0.5;}}
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar (same for all)
    with st.sidebar:
        if st.session_state.user:
            user_stats = get_user_stats(st.session_state.user[0])
            st.markdown(f"""
            <div class="user-info">
                <h3>{st.session_state.user[1]}</h3>
                <p>Role: <b>{st.session_state.user[2].upper()}</b></p>
                <hr>
                <p>Analyses: <b>{user_stats[0]}</b></p>
                <p>Records: <b>{user_stats[1]}</b></p>
                <p>Logins: <b>{user_stats[2]}</b></p>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("Logout", use_container_width=True):
            logout_user(st.session_state.user[0])
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    
    if st.session_state.user[2] == 'admin':
        # === ADMIN PANEL ===
        st.markdown('<div class="main-header">Admin Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Complete Lead Scoring Management</div>', unsafe_allow_html=True)
        
        admin_tab1, admin_tab2 = st.tabs(["Lead Scoring", "User Management"])
        
        with admin_tab1:
            # Your FULL lead scoring app here (file upload, models, charts, downloads)
            uploaded_file = st.file_uploader("Upload Excel leads", type=['xlsx'])
            if uploaded_file:
                # ... (paste ALL your existing main() logic here - unchanged)
                pass  # Models train, scores generate, charts show, Excel download
        
        with admin_tab2:
            # User management tabs (identical to AI PPT)
            user_tab1, user_tab2, user_tab3 = st.tabs(["Live Users", "Manage Users", "Activity"])
            
            with user_tab1:
                active_users = get_currently_loggedin_users()
                if active_users:
                    for user in active_users:
                        st.markdown(f"""
                        <div style="background: #e8f5e9; padding:15px; border-radius:8px; margin:10px 0;">
                            <span class="online-indicator"></span>
                            <b>{user[1]}</b> ({user[4]})<br>
                            <small>{user[2] or 'N/A'} | {user[3]}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No users online")
            
            with user_tab2:
                users = get_all_users()
                userdata = [[u[0], u[1], u[2] or 'N/A', u[3], 'Yes' if u[5] else 'No', u[6]] for u in users]
                df_users = pd.DataFrame(userdata, columns=['ID', 'Username', 'Email', 'Created', 'Active', 'Role'])
                st.dataframe(df_users)
                
                col1, col2, col3 = st.columns(3)
                with col1: user_id = st.number_input("User ID", min_value=1)
                with col2: action = st.selectbox("Action", ["Enable", "Disable", "Delete"])
                with col3:
                    if st.button("Execute", type="primary"):
                        if action == "Enable": toggle_user_status(user_id, 1)
                        elif action == "Disable": toggle_user_status(user_id, 0)
                        elif action == "Delete": delete_user(user_id)
                        st.rerun()
            
            with user_tab3:
                # Activity log DataFrame (same as AI PPT)
                pass  # Add get_all_user_activities() if needed
    
    else:
        # === USER PANEL (Lead Scoring Only) ===
        st.markdown('<div class="main-header">Lead Scoring Pro</div>', unsafe_allow_html=True)
        # Your FULL lead scoring logic here (upload → score → download)
        # No admin tabs, just the core app
    
    # Footer
    sys_stats = get_system_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Users", sys_stats[0])
    with col2: st.metric("Online", sys_stats[1])
    with col3: st.metric("Analyses", sys_stats[2])
    with col4: st.metric("Records", sys_stats[3])

if __name__ == "__main__":
    main()
