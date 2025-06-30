import os
import secrets
from urllib.parse import urlencode

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

LINE_CLIENT_ID = os.getenv("LINE_CHANNEL_ID")
LINE_CLIENT_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_REDIRECT_URI = os.getenv("LINE_REDIRECT_URI", "http://localhost:8080")

AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
PROFILE_URL = "https://api.line.me/v2/profile"


def _login_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": LINE_CLIENT_ID,
        "redirect_uri": LINE_REDIRECT_URI,
        "scope": "profile openid",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _exchange_code(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_REDIRECT_URI,
        "client_id": LINE_CLIENT_ID,
        "client_secret": LINE_CLIENT_SECRET,
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()


def _fetch_profile(access_token: str) -> dict:
    resp = requests.get(PROFILE_URL, headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.json()


def ensure_login() -> None:
    """Ensure user has logged in via LINE. Stops execution if not."""
    if "line_access_token" in st.session_state:
        return

    params = st.query_params.to_dict()
    if "code" in params:
        code = params["code"][0]
        state = params.get("state", [None])[0]
        if state != st.session_state.get("line_oauth_state"):
            st.error("State mismatch. Please try again.")
            st.stop()
        try:
            token_data = _exchange_code(code)
            st.session_state["line_access_token"] = token_data["access_token"]
            st.session_state["line_id_token"] = token_data.get("id_token")
            st.session_state["line_profile"] = _fetch_profile(token_data["access_token"])
            # remove query params
            st.query_params.clear()
            return
        except Exception as exc:
            st.error(f"Login failed: {exc}")
            st.stop()

    state = secrets.token_hex(16)
    st.session_state["line_oauth_state"] = state
    login_url = _login_url(state)
    st.markdown(f"[LINE Login]({login_url})")
    st.stop()
