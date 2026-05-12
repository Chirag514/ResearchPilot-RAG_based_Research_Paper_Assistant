import copy
import uuid
import streamlit as st
from backend.clients import get_supabase_admin


def _user_id() -> str:
    uid = st.session_state.get("user_id")
    # FIX: never persist state for unauthenticated users —
    # "anonymous" is not a real user ID and could collide across sessions.
    if not uid or uid == "anonymous":
        return None
    return uid


def load_state() -> dict:
    """Load persisted state for the current authenticated user."""
    uid = _user_id()
    if uid:
        try:
            sb  = get_supabase_admin()
            res = (
                sb.table("chat_state")
                .select("data")
                .eq("user_id", uid)
                .order("id", desc=True)
                .limit(1)
                .execute()
            )
            if res.data:
                raw = res.data[0]["data"]
                # Migrate legacy pdf_bytes → pdf_paths
                for sess in raw.get("sessions", {}).values():
                    sess.pop("pdf_bytes", None)
                    sess.setdefault("pdf_paths", {})
                    sess.setdefault("messages",  [])
                    sess.setdefault("papers",    [])
                    sess.setdefault("analysis",  {})
                return raw
        except Exception as e:
            st.warning(f"Could not load state: {e}")

    first_id = uuid.uuid4().hex[:8]
    return {
        "sessions": {
            "Chat 1": {
                "id":        first_id,
                "messages":  [],
                "papers":    [],
                "analysis":  {},
                "pdf_paths": {}
            }
        },
        "active":  "Chat 1",
        "counter": 1,
    }


def _build_save_data() -> dict:
    """Build the dict to be persisted. Always called fresh — no references to live objects."""
    data = {
        "sessions": {},
        "active":   st.session_state.active_session,
        "counter":  st.session_state.session_counter,
    }
    for name, sess in st.session_state.chat_sessions.items():
        data["sessions"][name] = {
            "id":        sess["id"],
            # Deep-copy messages so the saved snapshot is not a live reference.
            "messages":  copy.deepcopy(sess.get("messages",  [])),
            "papers":    list(sess.get("papers",    [])),
            "analysis":  dict(sess.get("analysis",  {})),
            "pdf_paths": dict(sess.get("pdf_paths", {})),
        }
    return data


def save_state():
    # FIX: skip save entirely for unauthenticated / anonymous users
    uid = _user_id()
    if not uid:
        return

    data = _build_save_data()

    # Compare against last saved snapshot to avoid redundant writes.
    if data == st.session_state.get("last_saved_state"):
        return

    try:
        sb = get_supabase_admin()

        existing = sb.table("chat_state").select("id").eq("user_id", uid).execute()

        if existing.data:
            sb.table("chat_state") \
              .update({"data": data}) \
              .eq("user_id", uid) \
              .execute()
        else:
            sb.table("chat_state") \
              .insert({"user_id": uid, "data": data}) \
              .execute()

        # Store a deep copy so future mutations to session_state don't
        # silently corrupt the "already saved" reference.
        st.session_state.last_saved_state = copy.deepcopy(data)

    except Exception as e:
        st.error(f"❌ Save failed: {e}")