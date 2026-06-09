import json
import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import pandas as pd
import streamlit as st
from data_utils import generate_mock_feedback_data


NOTIFICATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notifications.json")
NOTIFICATION_RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notification_rules.json")
EMAIL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_config.json")
DISPLAY_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "display_config.json")


DEFAULT_ALERT_RULES = {
    "feedback_volume": {
        "enabled": True,
        "name": "反馈数量预警",
        "description": "当指定时间窗口内新增反馈数量超过阈值时触发预警",
        "threshold": 10,
        "time_window_hours": 48,
        "severity": "warning",
        "notify_channels": ["in_app"]
    },
    "urgent_bug": {
        "enabled": True,
        "name": "紧急Bug报告预警",
        "description": "当检测到包含紧急关键词的Bug报告时立即触发预警",
        "urgent_keywords": ["崩溃", "闪退", "黑屏", "无法登录", "数据丢失", "宕机", "严重", "紧急", "无法使用", "error", "bug"],
        "severity": "critical",
        "notify_channels": ["in_app", "email"]
    },
    "negative_sentiment": {
        "enabled": False,
        "name": "负面情感激增预警",
        "description": "当负面情感反馈占比超过阈值时触发预警",
        "threshold_percent": 40,
        "time_window_hours": 24,
        "severity": "warning",
        "notify_channels": ["in_app"]
    },
    "pending_backlog": {
        "enabled": False,
        "name": "待处理积压预警",
        "description": "当待处理反馈数量超过阈值时触发预警",
        "threshold": 50,
        "severity": "info",
        "notify_channels": ["in_app"]
    }
}


DEFAULT_USER_SUBSCRIPTION = {
    "enabled": True,
    "subscribed_rules": [
        "feedback_volume",
        "urgent_bug",
        "negative_sentiment",
        "pending_backlog"
    ],
    "rule_channels": {
        "feedback_volume": ["in_app"],
        "urgent_bug": ["in_app", "email"],
        "negative_sentiment": ["in_app"],
        "pending_backlog": ["in_app"]
    }
}


DEFAULT_EMAIL_CONFIG = {
    "enabled": False,
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "noreply@example.com",
    "smtp_password": "",
    "sender_name": "反馈分析系统",
    "default_recipients": ["admin@example.com"]
}


DEFAULT_DISPLAY_CONFIG = {
    "show_sidebar_notification": True,
    "show_top_badge": True
}


NOTIFICATION_CHANNELS = {
    "in_app": {
        "name": "站内消息",
        "description": "在系统通知中心显示"
    },
    "email": {
        "name": "邮件通知",
        "description": "发送邮件到指定邮箱"
    }
}


SEVERITY_LEVELS = {
    "info": {"name": "信息", "color": "#636EFA", "icon": "ℹ️"},
    "warning": {"name": "警告", "color": "#FFA15A", "icon": "⚠️"},
    "critical": {"name": "紧急", "color": "#EF553B", "icon": "🚨"}
}


def init_notification_system():
    if "notifications_initialized" not in st.session_state:
        load_notification_rules()
        load_notifications()
        load_email_config()
        load_display_config()
        if "show_notification_popup" not in st.session_state:
            st.session_state.show_notification_popup = False
        st.session_state.notifications_initialized = True


def load_notification_rules():
    if not os.path.exists(NOTIFICATION_RULES_FILE):
        save_notification_rules(DEFAULT_ALERT_RULES)
        return DEFAULT_ALERT_RULES
    try:
        with open(NOTIFICATION_RULES_FILE, "r", encoding="utf-8") as f:
            rules = json.load(f)
        for key, default in DEFAULT_ALERT_RULES.items():
            if key not in rules:
                rules[key] = default
        return rules
    except (json.JSONDecodeError, IOError):
        return DEFAULT_ALERT_RULES


def save_notification_rules(rules):
    with open(NOTIFICATION_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def load_user_subscriptions():
    rules = load_notification_rules()
    subscriptions = rules.get("user_subscriptions", {})
    if "default" not in subscriptions:
        subscriptions["default"] = DEFAULT_USER_SUBSCRIPTION.copy()
    return subscriptions


def save_user_subscriptions(subscriptions):
    rules = load_notification_rules()
    rules["user_subscriptions"] = subscriptions
    save_notification_rules(rules)


def get_user_subscription(username=None):
    subscriptions = load_user_subscriptions()
    if username is None:
        try:
            from auth_utils import get_current_user
            user = get_current_user()
            if user:
                username = user.get("username")
        except (ImportError, Exception):
            pass
    if username and username in subscriptions:
        user_sub = subscriptions[username].copy()
        for key, default_val in DEFAULT_USER_SUBSCRIPTION.items():
            if key not in user_sub:
                user_sub[key] = default_val
        if "rule_channels" in user_sub:
            for rule_id, default_channels in DEFAULT_USER_SUBSCRIPTION["rule_channels"].items():
                if rule_id not in user_sub["rule_channels"]:
                    user_sub["rule_channels"][rule_id] = default_channels
        return user_sub
    return subscriptions.get("default", DEFAULT_USER_SUBSCRIPTION).copy()


def save_user_subscription(username, subscription):
    subscriptions = load_user_subscriptions()
    subscriptions[username] = subscription
    save_user_subscriptions(subscriptions)


def is_user_subscribed_to_rule(username, rule_id):
    user_sub = get_user_subscription(username)
    if not user_sub.get("enabled", True):
        return False
    return rule_id in user_sub.get("subscribed_rules", [])


def get_user_channels_for_rule(username, rule_id):
    user_sub = get_user_subscription(username)
    if not user_sub.get("enabled", True):
        return []
    if not is_user_subscribed_to_rule(username, rule_id):
        return []
    return user_sub.get("rule_channels", {}).get(rule_id, [])


def load_email_config():
    if not os.path.exists(EMAIL_CONFIG_FILE):
        save_email_config(DEFAULT_EMAIL_CONFIG)
        return DEFAULT_EMAIL_CONFIG.copy()
    try:
        with open(EMAIL_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key, default in DEFAULT_EMAIL_CONFIG.items():
            if key not in config:
                config[key] = default
        return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_EMAIL_CONFIG.copy()


def save_email_config(config):
    with open(EMAIL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_display_config():
    if not os.path.exists(DISPLAY_CONFIG_FILE):
        save_display_config(DEFAULT_DISPLAY_CONFIG)
        return DEFAULT_DISPLAY_CONFIG.copy()
    try:
        with open(DISPLAY_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key, default in DEFAULT_DISPLAY_CONFIG.items():
            if key not in config:
                config[key] = default
        return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_DISPLAY_CONFIG.copy()


def save_display_config(config):
    with open(DISPLAY_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_notifications():
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_notifications(notifications):
    with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(notifications, f, ensure_ascii=False, indent=2)


def _get_current_username():
    try:
        from auth_utils import get_current_user
        user = get_current_user()
        if user:
            return user.get("username")
    except (ImportError, Exception):
        pass
    return None


def _get_all_user_usernames():
    try:
        from auth_utils import get_users
        users = get_users()
        return [u["username"] for u in users]
    except (ImportError, Exception):
        return []


def create_notification(rule_id, rule_name, severity, message, details=None, channels=None, target_username=None):
    notifications = load_notifications()
    created_notifications = []

    if target_username:
        target_users = [target_username]
    else:
        target_users = _get_all_user_usernames()
        if not target_users:
            target_users = [None]

    for username in target_users:
        effective_channels = channels or ["in_app"]

        if username:
            if not is_user_subscribed_to_rule(username, rule_id):
                continue
            user_channels = get_user_channels_for_rule(username, rule_id)
            if user_channels:
                effective_channels = list(set(effective_channels) & set(user_channels)) if channels else user_channels
            if not effective_channels:
                continue

        notification = {
            "id": f"NOTIF-{uuid.uuid4().hex[:10].upper()}",
            "rule_id": rule_id,
            "rule_name": rule_name,
            "severity": severity,
            "message": message,
            "details": details or {},
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "read": False,
            "channels": effective_channels,
            "target_user": username
        }
        notifications.insert(0, notification)
        created_notifications.append(notification)

        email_config = load_email_config()
        if "email" in effective_channels and email_config.get("enabled", False):
            send_email_notification(notification, username)

    if len(notifications) > 500:
        notifications = notifications[:500]
    save_notifications(notifications)

    if len(created_notifications) == 1:
        return created_notifications[0]
    return created_notifications


def mark_as_read(notification_id, username=None):
    if username is None:
        username = _get_current_username()
    notifications = load_notifications()
    for n in notifications:
        if n["id"] == notification_id:
            if username is None or n.get("target_user") in (username, None):
                n["read"] = True
                break
    save_notifications(notifications)


def mark_all_as_read(username=None):
    if username is None:
        username = _get_current_username()
    notifications = load_notifications()
    for n in notifications:
        if username is None or n.get("target_user") in (username, None):
            n["read"] = True
    save_notifications(notifications)


def get_unread_count(username=None):
    if username is None:
        username = _get_current_username()
    notifications = load_notifications()
    count = 0
    for n in notifications:
        if not n.get("read", False):
            if username is None or n.get("target_user") in (username, None):
                count += 1
    return count


def get_notifications(limit=50, unread_only=False, username=None):
    if username is None:
        username = _get_current_username()
    notifications = load_notifications()
    filtered = []
    for n in notifications:
        if unread_only and n.get("read", False):
            continue
        if username is None or n.get("target_user") in (username, None):
            filtered.append(n)
    return filtered[:limit]


def delete_notification(notification_id, username=None):
    if username is None:
        username = _get_current_username()
    notifications = load_notifications()
    notifications = [n for n in notifications if not (
        n["id"] == notification_id and
        (username is None or n.get("target_user") in (username, None))
    )]
    save_notifications(notifications)


def clear_all_notifications(username=None):
    if username is None:
        username = _get_current_username()
    if username is None:
        save_notifications([])
    else:
        notifications = load_notifications()
        notifications = [n for n in notifications if n.get("target_user") != username]
        save_notifications(notifications)


def check_feedback_volume_alert(rule):
    if not rule.get("enabled", True):
        return None
    
    threshold = rule.get("threshold", 20)
    time_window = rule.get("time_window_hours", 24)
    
    feedback_df = generate_mock_feedback_data()
    feedback_df["日期"] = pd.to_datetime(feedback_df["日期"])
    
    cutoff_time = datetime.now() - timedelta(hours=time_window)
    recent_feedback = feedback_df[feedback_df["日期"] >= cutoff_time]
    count = len(recent_feedback)
    
    if count >= threshold:
        return {
            "triggered": True,
            "message": f"过去 {time_window} 小时内新增反馈 {count} 条，超过阈值 {threshold} 条",
            "details": {
                "count": count,
                "threshold": threshold,
                "time_window_hours": time_window
            }
        }
    return None


def check_urgent_bug_alert(rule):
    if not rule.get("enabled", True):
        return None
    
    keywords = [kw.lower() for kw in rule.get("urgent_keywords", [])]
    
    feedback_df = generate_mock_feedback_data()
    feedback_df["日期"] = pd.to_datetime(feedback_df["日期"])
    
    cutoff_time = datetime.now() - timedelta(hours=48)
    recent_feedback = feedback_df[
        (feedback_df["日期"] >= cutoff_time) & 
        (feedback_df["反馈类型"] == "Bug 报告")
    ]
    
    urgent_bugs = []
    for _, row in recent_feedback.iterrows():
        content = str(row["反馈内容"]).lower()
        if any(kw in content for kw in keywords):
            urgent_bugs.append({
                "id": row["反馈ID"],
                "content": row["反馈内容"],
                "date": row["日期"].strftime("%Y-%m-%d %H:%M:%S")
            })
    
    if urgent_bugs:
        return {
            "triggered": True,
            "message": f"检测到 {len(urgent_bugs)} 条紧急Bug报告需要立即处理",
            "details": {
                "urgent_bugs": urgent_bugs,
                "count": len(urgent_bugs)
            }
        }
    return None


def check_negative_sentiment_alert(rule):
    if not rule.get("enabled", False):
        return None
    
    threshold = rule.get("threshold_percent", 40)
    time_window = rule.get("time_window_hours", 24)
    
    feedback_df = generate_mock_feedback_data()
    feedback_df["日期"] = pd.to_datetime(feedback_df["日期"])
    
    cutoff_time = datetime.now() - timedelta(hours=time_window)
    recent_feedback = feedback_df[feedback_df["日期"] >= cutoff_time]
    
    if len(recent_feedback) == 0:
        return None
    
    negative_count = len(recent_feedback[recent_feedback["情感类别"] == "负面"])
    negative_percent = (negative_count / len(recent_feedback)) * 100
    
    if negative_percent >= threshold:
        return {
            "triggered": True,
            "message": f"过去 {time_window} 小时负面情感占比 {negative_percent:.1f}%，超过阈值 {threshold}%",
            "details": {
                "negative_percent": round(negative_percent, 1),
                "threshold_percent": threshold,
                "negative_count": negative_count,
                "total_count": len(recent_feedback)
            }
        }
    return None


def check_pending_backlog_alert(rule):
    if not rule.get("enabled", False):
        return None
    
    threshold = rule.get("threshold", 50)
    
    feedback_df = generate_mock_feedback_data()
    total_count = len(feedback_df)
    pending_count = int(total_count * 0.21)
    
    if pending_count >= threshold:
        return {
            "triggered": True,
            "message": f"当前待处理反馈 {pending_count} 条，超过阈值 {threshold} 条",
            "details": {
                "pending_count": pending_count,
                "threshold": threshold
            }
        }
    return None


def run_monitoring_checks():
    rules = load_notification_rules()
    new_notifications = []
    
    alert_checkers = {
        "feedback_volume": check_feedback_volume_alert,
        "urgent_bug": check_urgent_bug_alert,
        "negative_sentiment": check_negative_sentiment_alert,
        "pending_backlog": check_pending_backlog_alert
    }
    
    last_run = st.session_state.get("last_monitoring_run")
    now = datetime.now()
    
    if last_run:
        last_run_dt = pd.to_datetime(last_run)
        if (now - last_run_dt).total_seconds() < 30:
            return new_notifications
    
    st.session_state.last_monitoring_run = now.strftime("%Y-%m-%d %H:%M:%S")
    
    for rule_id, rule in rules.items():
        checker = alert_checkers.get(rule_id)
        if checker:
            result = checker(rule)
            if result and result.get("triggered"):
                last_notifs = get_notifications(limit=10)
                is_duplicate = any(
                    n.get("rule_id") == rule_id and 
                    (datetime.now() - pd.to_datetime(n["created_at"])).total_seconds() < 3600
                    for n in last_notifs
                )
                
                if not is_duplicate:
                    severity = rule.get("severity", "warning")
                    channels = rule.get("notify_channels", ["in_app"])
                    notification = create_notification(
                        rule_id=rule_id,
                        rule_name=rule.get("name", rule_id),
                        severity=severity,
                        message=result["message"],
                        details=result.get("details", {}),
                        channels=channels
                    )
                    new_notifications.append(notification)
    
    return new_notifications


def get_email_config():
    return load_email_config()


def _get_user_email(username):
    try:
        from auth_utils import get_user
        user = get_user(username)
        if user and user.get("email"):
            return user["email"]
    except (ImportError, Exception):
        pass
    return None


def send_email_notification(notification, target_username=None):
    try:
        config = load_email_config()

        if not config.get("enabled", False) or not config.get("smtp_password"):
            return False

        msg = MIMEMultipart()
        msg["From"] = Header(f"{config['sender_name']} <{config['smtp_user']}>", "utf-8")

        recipients = []
        if target_username:
            user_email = _get_user_email(target_username)
            if user_email:
                recipients = [user_email]
        if not recipients:
            recipients = config.get("default_recipients", [])
            if isinstance(recipients, str):
                recipients = [r.strip() for r in recipients.split("\n") if r.strip()]

        if not recipients:
            return False

        msg["To"] = ", ".join(recipients)

        severity_info = SEVERITY_LEVELS.get(notification["severity"], SEVERITY_LEVELS["info"])
        subject = f"{severity_info['icon']} [{severity_info['name']}] {notification['rule_name']}"
        msg["Subject"] = Header(subject, "utf-8")

        body = f"""
        <html>
        <body>
            <h2 style="color: {severity_info['color']};">{severity_info['icon']} {notification['rule_name']}</h2>
            <p><strong>通知时间：</strong>{notification['created_at']}</p>
            <p><strong>消息内容：</strong>{notification['message']}</p>
            <hr>
            <p style="color: #888; font-size: 12px;">此邮件由反馈分析系统自动发送，请勿直接回复。</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, "html", "utf-8"))

        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["smtp_user"], config["smtp_password"])
        server.sendmail(config["smtp_user"], recipients, msg.as_string())
        server.quit()

        return True
    except Exception as e:
        st.session_state["email_error"] = str(e)
        return False


def render_notification_icon():
    display_config = load_display_config()
    show_badge = display_config.get("show_top_badge", True)
    
    unread_count = get_unread_count()
    
    if show_badge:
        badge_html = f'<span style="position:absolute;top:-6px;right:-6px;background:#ef4444;color:white;border-radius:9999px;font-size:10px;font-weight:bold;padding:1px 6px;min-width:16px;text-align:center;">{unread_count}</span>' if unread_count > 0 else ''
    else:
        badge_html = ''
    
    icon_html = f"""
    <style>
    .top-notification-area {{
        position: fixed;
        top: 0.5rem;
        right: 4.5rem;
        z-index: 99999;
    }}
    </style>
    <div class="top-notification-area">
    """
    st.markdown(icon_html, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 6])
    with col1:
        bell_label = f"🔔 {unread_count}" if (show_badge and unread_count > 0) else "🔔"
        if st.button(bell_label, key="toggle_notification_popup", help="查看通知"):
            st.session_state.show_notification_popup = not st.session_state.show_notification_popup
            st.rerun()
    with col2:
        pass
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    return unread_count


def render_notification_popup():
    if not st.session_state.get("show_notification_popup", False):
        return
    
    unread = get_notifications(limit=10, unread_only=True)
    all_notifs = get_notifications(limit=10)
    
    st.markdown(
        """
        <style>
        .notification-popup-panel {
            position: fixed;
            top: 3.5rem;
            right: 1rem;
            width: 450px;
            max-height: calc(100vh - 5rem);
            overflow-y: auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            z-index: 99998;
            padding: 1rem;
            border: 1px solid #e5e7eb;
        }
        .notification-popup-panel .stButton button {
            width: 100%;
        }
        </style>
        <div class="notification-popup-panel">
        """,
        unsafe_allow_html=True
    )
    
    with st.container():
        st.markdown("### 🔔 通知中心")
        
        if not all_notifs:
            st.info("暂无通知")
        else:
            tab_unread, tab_all = st.tabs([f"未读 ({len(unread)})", "全部"])
            
            with tab_unread:
                if not unread:
                    st.info("没有未读通知")
                else:
                    for notif in unread:
                        _render_single_notification(notif, prefix="popup_unread")
            
            with tab_all:
                for notif in all_notifs:
                    _render_single_notification(notif, prefix="popup_all")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ 全部已读", use_container_width=True, key="popup_mark_all_read"):
                    mark_all_as_read()
                    st.rerun()
            with col2:
                if st.button("🗑️ 清空全部", use_container_width=True, key="popup_clear_all"):
                    clear_all_notifications()
                    st.rerun()
        
        st.markdown("---")
        if st.button("关闭通知面板", use_container_width=True, key="close_notification_popup"):
            st.session_state.show_notification_popup = False
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_single_notification(notification, prefix=""):
    severity = notification.get("severity", "info")
    sev_info = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["info"])
    is_read = notification.get("read", False)
    
    bg_opacity = "0.05" if is_read else "0.1"
    
    with st.container():
        st.markdown(
            f"""
            <div style="
                padding: 0.5rem 0.75rem;
                margin-bottom: 0.5rem;
                border-radius: 0.5rem;
                background-color: {sev_info['color']}{bg_opacity};
                border-left: 3px solid {sev_info['color']};
                opacity: {0.6 if is_read else 1.0};
            ">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div style="font-weight: bold; font-size: 0.9rem;">
                            {sev_info['icon']} {notification['rule_name']}
                        </div>
                        <div style="font-size: 0.8rem; margin-top: 0.25rem;">
                            {notification['message']}
                        </div>
                        <div style="font-size: 0.7rem; color: #888; margin-top: 0.25rem;">
                            {notification['created_at']}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        col_read, col_delete = st.columns([1, 1])
        with col_read:
            if not is_read:
                if st.button("✓ 已读", key=f"{prefix}_read_{notification['id']}", use_container_width=True):
                    mark_as_read(notification["id"])
                    st.rerun()
        with col_delete:
            if st.button("🗑️ 删除", key=f"{prefix}_del_{notification['id']}", use_container_width=True):
                delete_notification(notification["id"])
                st.rerun()
        
        if notification.get("details") and notification["details"]:
            with st.expander("📋 查看详情", expanded=False):
                details = notification["details"]
                if isinstance(details, dict):
                    for k, v in details.items():
                        if isinstance(v, list):
                            st.markdown(f"**{k}**:")
                            for item in v:
                                if isinstance(item, dict):
                                    st.json(item)
                                else:
                                    st.markdown(f"- {item}")
                        else:
                            st.markdown(f"**{k}**: {v}")
                else:
                    st.write(details)
        
        st.markdown("---")


def render_notification_history():
    st.markdown("### 📜 通知历史记录")
    
    notifications = load_notifications()
    
    if not notifications:
        st.info("暂无通知历史记录")
        return
    
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("总通知数", len(notifications))
    with col_stats2:
        unread = len([n for n in notifications if not n["read"]])
        st.metric("未读通知", unread)
    with col_stats3:
        critical = len([n for n in notifications if n.get("severity") == "critical"])
        st.metric("紧急通知", critical)
    
    st.markdown("---")
    
    severity_filter = st.multiselect(
        "按严重程度筛选",
        options=list(SEVERITY_LEVELS.keys()),
        format_func=lambda x: f"{SEVERITY_LEVELS[x]['icon']} {SEVERITY_LEVELS[x]['name']}",
        default=list(SEVERITY_LEVELS.keys())
    )
    
    filtered = [n for n in notifications if n.get("severity", "info") in severity_filter]
    
    for notif in filtered:
        _render_single_notification(notif, prefix="history")
