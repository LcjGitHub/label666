import streamlit as st
import pandas as pd
from auth_utils import (
    init_session,
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    require_permission,
    get_current_user,
    get_users
)
from sidebar_config import render_sidebar, render_sidebar_notification_center
from notification_utils import (
    init_notification_system,
    load_notification_rules,
    save_notification_rules,
    load_email_config,
    save_email_config,
    load_display_config,
    save_display_config,
    DEFAULT_ALERT_RULES,
    DEFAULT_USER_SUBSCRIPTION,
    NOTIFICATION_CHANNELS,
    SEVERITY_LEVELS,
    render_notification_icon,
    render_notification_popup,
    render_notification_history,
    run_monitoring_checks,
    create_notification,
    get_unread_count,
    send_email_notification,
    get_user_subscription,
    save_user_subscription,
    load_user_subscriptions,
    is_user_subscribed_to_rule,
    get_user_channels_for_rule
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
    filters = render_sidebar(current_page="notifications")

if not require_permission("edit_config"):
    st.stop()

st.title("🔔 通知设置")
st.markdown("---")

tab_rules, tab_subscription, tab_channels, tab_history = st.tabs([
    "⚙️ 预警规则配置",
    "📝 订阅规则配置",
    "📨 通知渠道设置",
    "📜 通知历史记录"
])

with tab_rules:
    st.subheader("预警规则配置")
    st.markdown("配置系统自动监控的预警规则，当满足条件时将触发通知。")
    st.markdown("---")
    
    rules = load_notification_rules()
    
    all_rule_configs = {}
    
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
            
            rule_params = {}
            
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
                rule_params = {"threshold": threshold, "time_window_hours": time_window}
            
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
                rule_params = {"urgent_keywords": [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]}
            
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
                rule_params = {"threshold_percent": threshold_percent, "time_window_hours": time_window_sent}
            
            elif rule_id == "pending_backlog":
                threshold_pending = st.number_input(
                    "待处理数量阈值",
                    min_value=1,
                    max_value=1000,
                    value=current_rule.get("threshold", 50),
                    key=f"threshold_pending_{rule_id}",
                    help="当待处理反馈数量超过此值时触发预警"
                )
                rule_params = {"threshold": threshold_pending}
            
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
            
            all_rule_configs[rule_id] = {
                "enabled": enabled,
                "name": current_rule.get("name", rule.get("name", rule_id)),
                "description": current_rule.get("description", rule.get("description", "")),
                "severity": severity,
                "notify_channels": selected_channels,
                **rule_params
            }
            
            col_save_single, col_test_single = st.columns([1, 1])
            
            with col_save_single:
                if st.button("💾 保存此规则", use_container_width=True, type="primary", key=f"save_single_{rule_id}"):
                    rules[rule_id] = all_rule_configs[rule_id]
                    save_notification_rules(rules)
                    st.success("✅ 规则配置已保存！")
                    st.rerun()
            
            with col_test_single:
                if st.button("🧪 测试通知", use_container_width=True, key=f"test_{rule_id}"):
                    test_notif = create_notification(
                        rule_id=rule_id,
                        rule_name=all_rule_configs[rule_id]["name"],
                        severity=severity,
                        message="这是一条测试通知，用于验证通知系统是否正常工作。",
                        details={"test": True, "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")},
                        channels=selected_channels
                    )
                    sev_info = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["warning"])
                    st.success(f"✅ 测试通知已发送！通知ID: {test_notif['id']}")
                    st.toast(f"{sev_info['icon']} 测试通知已创建", icon=sev_info["icon"])
    
    st.markdown("---")
    col_save_all, col_reset_all = st.columns(2)
    with col_save_all:
        if st.button("💾 保存所有规则", use_container_width=True, type="primary"):
            for rule_id, config in all_rule_configs.items():
                rules[rule_id] = config
            save_notification_rules(rules)
            st.success("✅ 所有规则已成功保存到配置文件！")
            st.rerun()
    with col_reset_all:
        if st.button("🔄 恢复所有默认设置", use_container_width=True):
            save_notification_rules(DEFAULT_ALERT_RULES.copy())
            st.success("✅ 所有规则已恢复默认设置")
            st.rerun()

with tab_subscription:
    st.subheader("订阅规则配置")
    st.markdown("为每个用户配置个性化的通知订阅规则，选择需要接收的通知类型和接收渠道。")
    st.markdown("---")
    
    users = get_users()
    current_user = get_current_user()
    all_usernames = [u["username"] for u in users]
    
    col_user_select, col_info = st.columns([1, 2])
    
    with col_user_select:
        target_username = st.selectbox(
            "选择用户",
            options=all_usernames,
            index=all_usernames.index(current_user["username"]) if current_user and current_user["username"] in all_usernames else 0,
            format_func=lambda x: next((f"{u.get('full_name', x)} ({x})" for u in users if u["username"] == x), x)
        )
    
    with col_info:
        target_user_info = next((u for u in users if u["username"] == target_username), None)
        if target_user_info:
            st.info(f"**用户**: {target_user_info.get('full_name', target_username)}  \n**邮箱**: {target_user_info.get('email', '未设置')}  \n**角色**: {target_user_info.get('role', '未知')}")
    
    user_sub = get_user_subscription(target_username)
    rules = load_notification_rules()
    
    st.markdown("---")
    
    col_enabled, col_quick = st.columns([1, 2])
    
    with col_enabled:
        sub_enabled = st.checkbox(
            "启用通知订阅",
            value=user_sub.get("enabled", True),
            help="关闭后该用户将不会收到任何通知"
        )
    
    with col_quick:
        st.markdown("**快捷操作**")
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            if st.button("📋 全选所有规则", use_container_width=True):
                user_sub["subscribed_rules"] = list(DEFAULT_ALERT_RULES.keys())
                st.rerun()
        with col_q2:
            if st.button("❌ 清空所有订阅", use_container_width=True):
                user_sub["subscribed_rules"] = []
                st.rerun()
        with col_q3:
            if st.button("🔄 恢复默认设置", use_container_width=True):
                user_sub = DEFAULT_USER_SUBSCRIPTION.copy()
                st.rerun()
    
    st.markdown("---")
    st.markdown("### 📋 通知类型订阅")
    st.markdown("勾选需要接收的通知类型，取消勾选将不再接收该类通知。")
    
    subscribed_rules = user_sub.get("subscribed_rules", list(DEFAULT_ALERT_RULES.keys()))
    rule_channels = user_sub.get("rule_channels", DEFAULT_USER_SUBSCRIPTION["rule_channels"].copy())
    
    new_subscribed_rules = []
    new_rule_channels = rule_channels.copy()
    
    for rule_id, default_rule in DEFAULT_ALERT_RULES.items():
        current_rule = rules.get(rule_id, default_rule)
        rule_name = current_rule.get("name", default_rule.get("name", rule_id))
        rule_desc = current_rule.get("description", default_rule.get("description", ""))
        severity = current_rule.get("severity", default_rule.get("severity", "warning"))
        sev_info = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["warning"])
        rule_enabled = current_rule.get("enabled", True)
        
        is_checked = rule_id in subscribed_rules
        
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 0.75rem; border-radius: 0.5rem; background-color: {sev_info['color']}15; border-left: 4px solid {sev_info['color']}; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <strong>{sev_info['icon']} {rule_name}</strong>
                            <div style="font-size: 0.85rem; color: #666; margin-top: 0.25rem;">{rule_desc}</div>
                            <div style="font-size: 0.8rem; color: #888; margin-top: 0.25rem;">
                                规则状态：{'<span style="color: green;">✅ 已启用</span>' if rule_enabled else '<span style="color: #999;">⏸️ 已禁用</span>'}
                                &nbsp;&nbsp;|&nbsp;&nbsp;
                                严重程度：{sev_info['name']}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            col_sub, col_ch = st.columns([1, 3])
            
            with col_sub:
                sub_this = st.checkbox(
                    "订阅此通知",
                    value=is_checked,
                    key=f"sub_{target_username}_{rule_id}",
                    disabled=not sub_enabled
                )
                if sub_this:
                    new_subscribed_rules.append(rule_id)
            
            with col_ch:
                if sub_this and sub_enabled:
                    st.markdown("**接收渠道**:")
                    current_channels = new_rule_channels.get(rule_id, default_rule.get("notify_channels", ["in_app"]))
                    selected_chs = []
                    ch_cols = st.columns(len(NOTIFICATION_CHANNELS))
                    for idx, (ch_id, ch_info) in enumerate(NOTIFICATION_CHANNELS.items()):
                        with ch_cols[idx]:
                            if st.checkbox(
                                f"{ch_info['name']}",
                                value=(ch_id in current_channels),
                                key=f"ch_{target_username}_{rule_id}_{ch_id}",
                                help=ch_info["description"]
                            ):
                                selected_chs.append(ch_id)
                    if selected_chs:
                        new_rule_channels[rule_id] = selected_chs
        
        st.markdown("---")
    
    st.markdown("### 📊 订阅概览")
    
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.metric("已订阅规则数", len(new_subscribed_rules), f"共 {len(DEFAULT_ALERT_RULES)} 个规则")
    with col_sum2:
        enabled_count = sum(1 for rid in new_subscribed_rules if rules.get(rid, {}).get("enabled", True))
        st.metric("有效订阅（规则已启用）", enabled_count)
    with col_sum3:
        has_email = any("email" in new_rule_channels.get(rid, []) for rid in new_subscribed_rules)
        st.metric("邮件通知", "已启用" if has_email else "未启用")
    
    st.markdown("---")
    
    col_save, col_test = st.columns([1, 1])
    
    with col_save:
        if st.button("💾 保存订阅设置", use_container_width=True, type="primary"):
            new_subscription = {
                "enabled": sub_enabled,
                "subscribed_rules": new_subscribed_rules,
                "rule_channels": new_rule_channels
            }
            save_user_subscription(target_username, new_subscription)
            st.success(f"✅ 用户「{target_username}」的订阅规则已保存！")
            st.rerun()
    
    with col_test:
        if st.button("🧪 发送测试通知", use_container_width=True):
            test_rules_to_send = new_subscribed_rules if sub_enabled else []
            if not test_rules_to_send:
                st.warning("⚠️ 当前没有订阅任何通知类型，请先订阅后测试。")
            else:
                test_rule_id = test_rules_to_send[0]
                test_rule = rules.get(test_rule_id, DEFAULT_ALERT_RULES.get(test_rule_id, {}))
                test_channels = new_rule_channels.get(test_rule_id, ["in_app"])
                test_notif = create_notification(
                    rule_id=test_rule_id,
                    rule_name=test_rule.get("name", test_rule_id),
                    severity=test_rule.get("severity", "warning"),
                    message=f"这是一条发送给「{target_username}」的订阅测试通知。",
                    details={"test": True, "test_user": target_username, "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")},
                    channels=test_channels,
                    target_username=target_username
                )
                if test_notif:
                    sev_info = SEVERITY_LEVELS.get(test_rule.get("severity", "warning"), SEVERITY_LEVELS["warning"])
                    st.success(f"✅ 测试通知已发送给「{target_username}」！通知ID: {test_notif['id']}")
                    st.toast(f"{sev_info['icon']} 测试通知已创建", icon=sev_info["icon"])
                else:
                    st.warning("⚠️ 通知未创建，请检查订阅设置和渠道配置。")

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
        current_display = load_display_config()
        show_in_sidebar = st.checkbox(
            "在侧边栏显示通知中心",
            value=current_display.get("show_sidebar_notification", True)
        )
        show_badge = st.checkbox(
            "在顶部显示未读数量角标",
            value=current_display.get("show_top_badge", True)
        )
        st.info(f"当前未读通知数量: **{get_unread_count()}**")
        
        if st.button("💾 保存显示设置", use_container_width=True, type="primary", key="save_display"):
            new_display_config = {
                "show_sidebar_notification": show_in_sidebar,
                "show_top_badge": show_badge
            }
            save_display_config(new_display_config)
            st.success("✅ 显示设置已保存！刷新页面后生效。")
            st.rerun()
    
    with col_ch2:
        st.markdown("### 📧 邮件通知")
        current_email = load_email_config()
        email_enabled = st.checkbox(
            "启用邮件通知",
            value=current_email.get("enabled", False),
            key="email_enabled"
        )
        
        if email_enabled:
            st.warning("⚠️ 邮件通知需要配置SMTP服务器信息")
            
            smtp_server = st.text_input(
                "SMTP服务器地址",
                value=current_email.get("smtp_server", "smtp.example.com")
            )
            smtp_port = st.number_input(
                "SMTP端口",
                min_value=1,
                max_value=65535,
                value=current_email.get("smtp_port", 587)
            )
            smtp_user = st.text_input(
                "SMTP用户名/发件邮箱",
                value=current_email.get("smtp_user", "noreply@example.com")
            )
            smtp_password = st.text_input(
                "SMTP密码/授权码",
                value=current_email.get("smtp_password", ""),
                type="password"
            )
            sender_name = st.text_input(
                "发件人名称",
                value=current_email.get("sender_name", "反馈分析系统")
            )
            
            st.markdown("#### 收件人设置")
            current_recipients = current_email.get("default_recipients", ["admin@example.com"])
            if isinstance(current_recipients, list):
                recipients_default = "\n".join(current_recipients)
            else:
                recipients_default = str(current_recipients)
            
            recipients_text = st.text_area(
                "默认收件人（每行一个邮箱）",
                value=recipients_default,
                height=100
            )
            
            col_test_email, col_save_email = st.columns(2)
            with col_test_email:
                if st.button("📤 发送测试邮件", use_container_width=True, key="test_email"):
                    if not smtp_password:
                        st.error("❌ 请填写SMTP密码")
                    else:
                        temp_config = {
                            "enabled": True,
                            "smtp_server": smtp_server,
                            "smtp_port": int(smtp_port),
                            "smtp_user": smtp_user,
                            "smtp_password": smtp_password,
                            "sender_name": sender_name,
                            "default_recipients": [r.strip() for r in recipients_text.split("\n") if r.strip()]
                        }
                        old_config = load_email_config()
                        save_email_config(temp_config)
                        
                        test_notif = create_notification(
                            rule_id="email_test",
                            rule_name="邮件渠道测试",
                            severity="info",
                            message="这是一封测试邮件，用于验证邮件通知渠道配置是否正确。",
                            details={"test": True},
                            channels=["email"]
                        )
                        
                        save_email_config(old_config)
                        
                        if st.session_state.get("email_error"):
                            st.error(f"❌ 发送失败: {st.session_state['email_error']}")
                        else:
                            st.success("✅ 测试邮件已发送，请检查收件箱")
            with col_save_email:
                if st.button("💾 保存邮件配置", use_container_width=True, type="primary", key="save_email"):
                    new_email_config = {
                        "enabled": email_enabled,
                        "smtp_server": smtp_server,
                        "smtp_port": int(smtp_port),
                        "smtp_user": smtp_user,
                        "smtp_password": smtp_password,
                        "sender_name": sender_name,
                        "default_recipients": [r.strip() for r in recipients_text.split("\n") if r.strip()]
                    }
                    save_email_config(new_email_config)
                    st.success("✅ 邮件配置已成功保存到配置文件！")
                    st.rerun()
        else:
            st.info("邮件通知渠道未启用。启用后需要配置SMTP服务器信息。")
            
            if st.button("💾 保存邮件配置", use_container_width=True, key="save_email_disabled"):
                new_email_config = {
                    "enabled": False,
                    "smtp_server": current_email.get("smtp_server", "smtp.example.com"),
                    "smtp_port": current_email.get("smtp_port", 587),
                    "smtp_user": current_email.get("smtp_user", "noreply@example.com"),
                    "smtp_password": current_email.get("smtp_password", ""),
                    "sender_name": current_email.get("sender_name", "反馈分析系统"),
                    "default_recipients": current_email.get("default_recipients", ["admin@example.com"])
                }
                save_email_config(new_email_config)
                st.success("✅ 邮件配置已保存")
                st.rerun()
    
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
