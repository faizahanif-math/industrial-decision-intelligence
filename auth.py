import bcrypt
import streamlit as st
from styles import apply_custom_theme


def check_login(username, password):
    from dashboard_utils import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, username, password_hash, full_name, role "
                "FROM users WHERE username = %s AND is_active = TRUE;",
                (username,)
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    user_id, uname, pwd_hash, full_name, role = row

    if bcrypt.checkpw(password.encode(), pwd_hash.encode()):
        return {
            "user_id": user_id,
            "username": uname,
            "full_name": full_name,
            "role": role,
        }
    return None


def login_page():
    apply_custom_theme()
    
    col_l, col_m, col_r = st.columns([1, 1.8, 1])
    with col_m:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px; margin-bottom: 25px;">
            <div style="display: inline-block; padding: 14px 18px; border-radius: 16px; background: rgba(2, 132, 199, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); margin-bottom: 12px;">
                <span style="font-size: 2.4rem;">🏭</span>
            </div>
            <h1 style="font-size: 1.85rem; font-weight: 800; margin: 0; background: linear-gradient(90deg, #FFFFFF, #93C5FD); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Industrial Decision Intelligence</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-top: 6px;">Enterprise Operational Intelligence & AI Risk Mitigation</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("#### 🔐 Secure System Access")
            st.caption("Enter authorized operator credentials to access plant telemetry.")
            username = st.text_input("Username", placeholder="e.g. admin")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In to Operations Console", type="primary", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            user = check_login(username, password)
            if user:
                st.session_state["user"] = user
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")


def logout_button():
    if "user" in st.session_state:
        user = st.session_state["user"]
        c_info, c_btn = st.columns([5, 1])
        with c_info:
            st.markdown(
                f"<div style='padding-top: 6px; color: #94A3B8; font-size: 0.88rem;'>"
                f"👤 Authenticated as: <strong style='color:#F8FAFC;'>{user['full_name']}</strong> "
                f"<span style='background:rgba(2, 132, 199, 0.2); color:#38BDF8; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 6px; border: 1px solid rgba(56, 189, 248, 0.3); font-weight: 600;'>{user['role']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        with c_btn:
            if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
                del st.session_state["user"]
                st.rerun()
