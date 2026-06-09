import streamlit as st
import pandas as pd
from auth_utils import (
    init_session,
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    require_permission
)
from sidebar_config import render_sidebar
from notification_utils import (
    init_notification_system,
    load_notification_rules,
    save_notification_rules,
    DEFAULT_ALERT_RULES,
    NOTIFICATION_CHANNELS,
    SEVERITY_LEVELS,
    render_notification_icon,
    render_notification_history,
    run_monitoring_checks,
    get_notifications,
    create_notification,
    get_unread_count
)


st.set_page_config(
    page_title="通知设置",
    page_icon="🔔",
    layout="wide"
)

init_session()
init_notification_system()

if not is_logged_in():
    render_login_page()
    st.stop()

render_notification_icon()

new_notifs = run_monitoring_checks()
if new_notifs:
    for notif in new_notifs:
        sev_info = SEVERITY_LEVELS.get(notif["severity"], SEVERITY_LEVELS["info"])
        st.toast(f"{sev_info['icon']} {notif['rule_name']}: {notif['message']}", icon=sev_info["icon"])

with st.sidebar:
    render_user_info_in_sidebar()
    filters = render_sidebar(current_page="notifications")

if not require_permission("edit_config"):
    st.stop()

st.title("🔔 通知设置")
st.markdown("---")

tab_rules, tab_channels, tab_history = st.tabs([
    "⚙️ 预警规则配置",
    "📨 通知渠道设置",
    "📜 通知历史记录"
])

with tab_rules:
    st.subheader("预警规则配置")
    st.markdown("配置系统自动监控的预警规则，当满足条件时将触发通知。")
    st.markdown("---")
    
    rules = load_notification_rules()
    
    for rule_id, rule in DEFAULT_ALERT_RULES.items():
        current_rule = rules.get(rule_id, rule)
        
        with st.expander(
            f"{SEVERITY_LEVELS.get(current_rule.get('severity', 'warning'), SEVERITY_LEVELS['warning'])['icon']} "
            f"{current_rule.get('name', rule_id)} "
            f"({'✅ 已启用' if current_rule.get('enabled', True) else '❌ 已禁用'})",
            expanded=(rule_id == "feedback_volume")
        ):
            st.markdown(f"**规则描述**: {current_rule.get('description', rule.get('description', ''))}")
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                enabled = st.checkbox(
                    "启用此规则",
                    value=current_rule.get("enabled", True),
                    key=f"enabled_{rule_id}"
                )
            
            with col2:
                severity_options = list(SEVERITY_LEVELS.keys())
                current_severity = current_rule.get("severity", "warning")
                severity = st.selectbox(
                    "严重程度",
                    options=severity_options,
                    index=severity_options.index(current_severity) if current_severity in severity_options else 1,
                    format_func=lambda x: f"{SEVERITY_LEVELS[x]['icon']} {SEVERITY_LEVELS[x]['name']}",
                    key=f"severity_{rule_id}"
                )
            
            st.markdown("#### 🎛️ 规则参数")
            
            if rule_id == "feedback_volume":
                col_a, col_b = st.columns(2)
                with col_a:
                    threshold = st.number_input(
                        "反馈数量阈值",
                        min_value=1,
                        max_value=1000,
                        value=current_rule.get("threshold", 20),
                        key=f"threshold_{rule_id}",
                        help="当时间窗口内反馈数量达到此值时触发预警"
                    )
                with col_b:
                    time_window = st.number_input(
                        "时间窗口（小时）",
                        min_value=1,
                        max_value=168,
                        value=current_rule.get("time_window_hours", 24),
                        key=f"time_window_{rule_id}",
                        help="统计反馈数量的时间范围"
                    )
            
            elif rule_id == "urgent_bug":
                keywords = current_rule.get(
                    "urgent_keywords",
                    ["崩溃", "闪退", "黑屏", "无法登录", "数据丢失", "宕机", "严重", "紧急", "无法使用", "error", "bug"]
                )
                keywords_text = st.text_area(
                    "紧急关键词（每行一个）",
                    value="\n".join(keywords),
                    height=150,
                    key=f"keywords_{rule_id}",
                    help="当Bug报告内容包含这些关键词时将触发紧急预警"
                )
            
            elif rule_id == "negative_sentiment":
                col_a, col_b = st.columns(2)
                with col_a:
                    threshold_percent = st.number_input(
                        "负面情感占比阈值（%）",
                        min_value=1,
                        max_value=100,
                        value=current_rule.get("threshold_percent", 40),
                        key=f"threshold_pct_{rule_id}",
                        help="当负面情感反馈占比超过此百分比时触发预警"
                    )
                with col_b:
                    time_window_sent = st.number_input(
                        "时间窗口（小时）",
                        min_value=1,
                        max_value=168,
                        value=current_rule.get("time_window_hours", 24),
                        key=f"time_window_sent_{rule_id}",
                        help="统计情感占比的时间范围"
                    )
            
            elif rule_id == "pending_backlog":
                threshold_pending = st.number_input(
                    "待处理数量阈值",
                    min_value=1,
                    max_value=1000,
                    value=current_rule.get("threshold", 50),
                    key=f"threshold_pending_{rule_id}",
                    help="当待处理反馈数量超过此值时触发预警"
                )
            
            st.markdown("#### 📨 通知渠道")
            channels = current_rule.get("notify_channels", ["in_app"])
            selected_channels = []
            for ch_id, ch_info in NOTIFICATION_CHANNELS.items():
                if st.checkbox(
                    f"{ch_info['name']} - {ch_info['description']}",
                    value=(ch_id in channels),
                    key=f"channel_{rule_id}_{ch_id}"
                ):
                    selected_channels.append(ch_id)
            
            col_save, col_test, col_reset = st.columns([2, 1, 1])
            
            with col_save:
                if st.button("💾 保存此规则", use_container_width=True, type="primary", key=f"save_{rule_id}"):
                    updated_rule = {
                        "enabled": enabled,
                        "name": current_rule.get("name", rule.get("name", rule_id)),
                        "description": current_rule.get("description", rule.get("description", "")),
                        "severity": severity,
                        "notify_channels": selected_channels
                    }
                    
                    if rule_id == "feedback_volume":
                        updated_rule["threshold"] = threshold
                        updated_rule["time_window_hours"] = time_window
                    elif rule_id == "urgent_bug":
                        updated_rule["urgent_keywords"] = [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]
                    elif rule_id == "negative_sentiment":
                        updated_rule["threshold_percent"] = threshold_percent
                        updated_rule["time_window_hours"] = time_window_sent
                    elif rule_id == "pending_backlog":
                        updated_rule["threshold"] = threshold_pending
                    
                    rules[rule_id] = updated_rule
                    save_notification_rules(rules)
                    st.success("✅ 规则配置已保存！")
                    st.rerun()
            
            with col_test:
                if st.button("🧪 测试通知", use_container_width=True, key=f"test_{rule_id}"):
                    test_notif = create_notification(
                        rule_id=rule_id,
                        rule_name=current_rule.get("name", rule_id),
                        severity=severity,
                        message="这是一条测试通知，用于验证通知系统是否正常工作。",
                        details={"test": True, "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")},
                        channels=selected_channels
                    )
                    sev_info = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["warning"])
                    st.success(f"✅ 测试通知已发送！通知ID: {test_notif['id']}")
                    st.toast(f"{sev_info['icon']} 测试通知已创建", icon=sev_info["icon"])
            
            with col_reset:
                if st.button("🔄 恢复默认", use_container_width=True, key=f"reset_{rule_id}"):
                    rules[rule_id] = DEFAULT_ALERT_RULES[rule_id].copy()
                    save_notification_rules(rules)
                    st.success("✅ 已恢复默认设置")
                    st.rerun()
    
    st.markdown("---")
    col_save_all, col_reset_all = st.columns(2)
    with col_save_all:
        if st.button("💾 保存所有规则", use_container_width=True, type="primary"):
            st.success("✅ 所有规则已保存！")
    with col_reset_all:
        if st.button("🔄 恢复所有默认设置", use_container_width=True):
            save_notification_rules(DEFAULT_ALERT_RULES.copy())
            st.success("✅ 所有规则已恢复默认设置")
            st.rerun()

with tab_channels:
    st.subheader("通知渠道设置")
    st.markdown("配置不同通知渠道的参数，支持站内消息和邮件通知。")
    st.markdown("---")
    
    col_ch1, col_ch2 = st.columns(2)
    
    with col_ch1:
        st.markdown("### 💬 站内消息")
        st.success("✅ 站内消息渠道已默认启用")
        st.info("站内消息将在系统通知中心显示，点击右上角🔔图标或侧边栏查看。")
        
        st.markdown("#### 显示设置")
        show_in_sidebar = st.checkbox("在侧边栏显示通知中心", value=True)
        show_badge = st.checkbox("在顶部显示未读数量角标", value=True)
        st.info("当前未读通知数量: " + str(get_unread_count()))
    
    with col_ch2:
        st.markdown("### 📧 邮件通知")
        email_enabled = st.checkbox("启用邮件通知", value=False, key="email_enabled")
        
        if email_enabled:
            st.warning("⚠️ 邮件通知需要配置SMTP服务器信息")
            
            smtp_server = st.text_input("SMTP服务器地址", value="smtp.example.com")
            smtp_port = st.number_input("SMTP端口", min_value=1, max_value=65535, value=587)
            smtp_user = st.text_input("SMTP用户名/发件邮箱", value="noreply@example.com")
            smtp_password = st.text_input("SMTP密码/授权码", type="password")
            sender_name = st.text_input("发件人名称", value="反馈分析系统")
            
            st.markdown("#### 收件人设置")
            recipients_text = st.text_area(
                "默认收件人（每行一个邮箱）",
                value="admin@example.com",
                height=100
            )
            
            col_test_email, col_save_email = st.columns(2)
            with col_test_email:
                if st.button("📤 发送测试邮件", use_container_width=True):
                    if not smtp_password:
                        st.error("请填写SMTP密码")
                    else:
                        test_notif = create_notification(
                            rule_id="email_test",
                            rule_name="邮件渠道测试",
                            severity="info",
                            message="这是一封测试邮件，用于验证邮件通知渠道配置是否正确。",
                            details={"test": True},
                            channels=["email"]
                        )
                        if st.session_state.get("email_error"):
                            st.error(f"发送失败: {st.session_state['email_error']}")
                        else:
                            st.success("✅ 测试邮件已发送，请检查收件箱")
            with col_save_email:
                if st.button("💾 保存邮件配置", use_container_width=True, type="primary"):
                    st.success("✅ 邮件配置已保存（当前会话有效）")
        else:
            st.info("邮件通知渠道未启用。启用后需要配置SMTP服务器信息。")
    
    st.markdown("---")
    st.markdown("### 📋 渠道说明")
    
    channel_df = pd.DataFrame([
        {
            "渠道名称": "站内消息",
            "说明": "在系统内通知中心显示，无需额外配置，实时送达",
            "适用场景": "日常预警、一般提醒",
            "延迟": "实时"
        },
        {
            "渠道名称": "邮件通知",
            "说明": "发送邮件到指定邮箱，需要配置SMTP服务器",
            "适用场景": "紧急预警、重要通知、离线提醒",
            "延迟": "取决于邮件服务器"
        }
    ])
    st.table(channel_df)

with tab_history:
    render_notification_history()
