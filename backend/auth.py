import streamlit as st
from backend.clients import get_supabase


def sign_up(email: str, password: str) -> dict:
    """Register a new user. Returns {'success': bool, 'message': str}."""
    try:
        sb  = get_supabase()
        res = sb.auth.sign_up({"email": email, "password": password})
        if res.user:
            return {"success": True, "message": "Account created!", "user": res.user, "session": res.session}
        return {"success": False, "message": "Sign up failed. Try again."}
    except Exception as e:
        return {"success": False, "message": str(e)}


def sign_in(email: str, password: str) -> dict:
    """Sign in existing user. Returns {'success': bool, 'message': str, 'user': ...}."""
    try:
        sb  = get_supabase()
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return {"success": True, "user": res.user, "session": res.session}
        return {"success": False, "message": "Invalid email or password."}
    except Exception as e:
        return {"success": False, "message": str(e)}


def sign_out():
    """Sign out current user and clear session state."""
    try:
        sb = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass
    # Clear all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_current_user():
    """Return current user object or None."""
    try:
        sb  = get_supabase()
        res = sb.auth.get_user()
        return res.user if res else None
    except Exception:
        return None


def is_authenticated() -> bool:
    """Check if a user is logged in."""
    return st.session_state.get("user") is not None