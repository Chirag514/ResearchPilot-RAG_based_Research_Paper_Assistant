import streamlit as st
from backend.auth import sign_in, sign_up


def render_auth_page():
    """Render login/signup page. Sets st.session_state.user on success."""

    # Remove negative top margin on auth page only
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 3rem !important;
            margin-top: 0rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0 1.5rem 0;">
                <h1>🔬 ResearchPilot : Research Paper Assistant</h1>
                <p style="opacity:0.6;">Sign in to access your papers and chat history</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

        # ── Login — uses st.form so Enter key submits ─────────────────────────
        with tab_login:
            st.markdown("#### Welcome back")
            with st.form("login_form"):
                email    = st.text_input("Email",    placeholder="you@example.com")
                password = st.text_input("Password", placeholder="••••••••", type="password")
                submitted = st.form_submit_button(
                    "Login", use_container_width=True, type="primary"
                )
            if submitted:
                if not email or not password:
                    st.warning("Please fill in all fields.")
                else:
                    with st.spinner("Signing in..."):
                        result = sign_in(email, password)
                    if result["success"]:
                        st.session_state.user    = result["user"]
                        st.session_state.user_id = result["user"].id
                        st.rerun()
                    else:
                        st.error(result["message"])

        # ── Sign Up — uses st.form so Enter key submits ───────────────────────
        with tab_signup:
            st.markdown("#### Create an account")
            with st.form("signup_form"):
                new_email    = st.text_input("Email",            placeholder="you@example.com")
                new_password = st.text_input("Password",         placeholder="Min 6 characters", type="password")
                confirm_pw   = st.text_input("Confirm Password", placeholder="Repeat password",  type="password")
                submitted_su = st.form_submit_button(
                    "Create Account", use_container_width=True, type="primary"
                )
            if submitted_su:
                if not new_email or not new_password or not confirm_pw:
                    st.warning("Please fill in all fields.")
                elif new_password != confirm_pw:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account..."):
                        result = sign_up(new_email, new_password)
                    if result["success"]:
                        # Auto-login if Supabase returned a session (email
                        # confirmation is disabled). Otherwise prompt to log in.
                        if result.get("session"):
                            st.session_state.user    = result["user"]
                            st.session_state.user_id = result["user"].id
                            st.rerun()
                        else:
                            st.success("Account created! Check your email to confirm, then log in.")
                    else:
                        st.error(result["message"])