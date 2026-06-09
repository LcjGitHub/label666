import streamlit as st
from auth_utils import (
    init_session,
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    render_user_management_page
)
from sidebar_config import render_sidebar_notification_center
from notification_utils import (
    init_notification_system,
    render_notification_icon,
    render_notification_popup,
    run_monitoring_checks,
    SEVERITY_LEVELS,
    load_display_config
)

st.set_page_config(
    page_title="用户管理",
    page_icon="👥",
    layout="wide"
)

init_session()
init_notification_system()

if not is_logged_in():
    render_login_page()
    st.stop()

render_notification_icon()
render_notification_popup()

new_notifs = run_monitoring_checks()
if new_notifs:
    for notif in new_notifs:
        sev_info = SEVERITY_LEVELS.get(notif["severity"], SEVERITY_LEVELS["info"])
        st.toast(f"{sev_info['icon']} {notif['rule_name']}: {notif['message']}", icon=sev_info["icon"])

with st.sidebar:
    render_user_info_in_sidebar()
    display_config = load_display_config()
    if display_config.get("show_sidebar_notification", True):
        render_sidebar_notification_center()

render_user_management_page()
