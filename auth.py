import bcrypt
import streamlit as st

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
    st.markdown("## 🔐 Login")
    st.caption("Please enter your credentials to access the dashboard.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

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
        col1, col2 = st.columns([4, 1])
        col1.write(f"👤 **{user['full_name']}**  ·  Role: `{user['role']}`")
        if col2.button("Logout"):
            del st.session_state["user"]
            st.rerun()