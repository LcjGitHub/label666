import streamlit as st
from auth_utils import (
    init_session,
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    render_user_management_page
)

st.set_page_config(
    page_title="用户管理",
    page_icon="👥",
    layout="wide"
)

init_session()

if not is_logged_in():
    render_login_page()
    st.stop()

with st.sidebar:
    render_user_info_in_sidebar()

render_user_management_page()
