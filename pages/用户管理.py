import streamlit as st
from auth_utils import (
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    render_user_management_page
)
from sidebar_config import render_sidebar

st.set_page_config(
    page_title="用户管理",
    page_icon="👥",
    layout="wide"
)

if not is_logged_in():
    render_login_page()
    st.stop()

with st.sidebar:
    render_user_info_in_sidebar()
    render_sidebar(current_page="users")

render_user_management_page()
