import streamlit as st
import pandas as pd
from datetime import datetime
from report_templates import get_available_items, REPORT_DEFAULT_TITLES
from notification_utils import (
    get_unread_count,
    get_notifications,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
    clear_all_notifications,
    SEVERITY_LEVELS
)

SIDEBAR_CONFIG = {
    "page_title": "用户反馈分析",
    "page_icon": "📊",
    "layout": "wide",
    "sections": [
        {
            "id": "filters",
            "title": "🔍 数据筛选",
            "expanded": True,
            "controls": [
                {
                    "id": "date_range",
                    "type": "date_input",
                    "label": "选择日期范围",
                    "help": "筛选指定日期范围内的数据",
                    "data_source": "date_range"
                },
                {
                    "id": "feedback_type",
                    "type": "multiselect",
                    "label": "选择反馈类型",
                    "help": "按反馈类型筛选数据",
                    "options": [
                        "功能建议",
                        "界面优化",
                        "性能问题",
                        "Bug 报告",
                        "使用咨询",
                        "其他"
                    ],
                    "default": "all"
                }
            ]
        },
        {
            "id": "sentiment_filters",
            "title": "💭 情感筛选",
            "expanded": True,
            "page_only": "sentiment",
            "controls": [
                {
                    "id": "sentiment_type",
                    "type": "multiselect",
                    "label": "选择情感类别",
                    "help": "按情感倾向筛选反馈数据",
                    "options": ["正面", "中性", "负面"],
                    "default": "all"
                }
            ]
        },
        {
            "id": "ticket_filters",
            "title": "🎫 工单筛选",
            "expanded": True,
            "page_only": "tickets",
            "controls": [
                {
                    "id": "ticket_search",
                    "type": "text_input",
                    "label": "搜索工单",
                    "help": "输入关键词搜索工单编号、标题、内容或备注"
                },
                {
                    "id": "ticket_status",
                    "type": "multiselect",
                    "label": "工单状态",
                    "help": "按状态筛选工单",
                    "options": ["待处理", "处理中", "已解决", "已关闭"],
                    "default": "all"
                },
                {
                    "id": "ticket_priority",
                    "type": "multiselect",
                    "label": "优先级",
                    "help": "按优先级筛选工单",
                    "options": ["低", "中", "高", "紧急"],
                    "default": "all"
                },
                {
                    "id": "ticket_assignee",
                    "type": "multiselect",
                    "label": "处理人",
                    "help": "按处理人筛选工单",
                    "options": ["张三", "李四", "王五", "赵六", "未分配"],
                    "default": "all"
                },
                {
                    "id": "ticket_date_range",
                    "type": "date_input",
                    "label": "创建日期范围",
                    "help": "按工单创建日期筛选",
                    "data_source": "date_range"
                }
            ]
        },
        {
            "id": "tips",
            "title": None,
            "expanded": True,
            "controls": [
                {
                    "id": "info_tip",
                    "type": "info",
                    "content": "💡 提示：使用上方筛选器来过滤数据，在页面顶部配置报告导出"
                }
            ]
        }
    ]
}


def render_report_export_section(page_type):
    charts, tables = get_available_items(page_type)
    
    with st.expander("📤 报告导出配置", expanded=False):
        st.markdown("#### 报告基本信息")
        
        title_key = f"report_title_{page_type}"
        if title_key not in st.session_state:
            st.session_state[title_key] = REPORT_DEFAULT_TITLES.get(page_type, "分析报告")
        report_title = st.text_input(
            "报告标题",
            key=title_key,
            help="设置导出报告的标题"
        )
        
        date_key = f"report_date_{page_type}"
        if date_key not in st.session_state:
            st.session_state[date_key] = datetime.now().date()
        report_date = st.date_input(
            "报告日期",
            key=date_key,
            help="选择报告生成日期"
        )
        
        notes_key = f"report_notes_{page_type}"
        if notes_key not in st.session_state:
            st.session_state[notes_key] = ""
        report_notes = st.text_area(
            "备注信息",
            key=notes_key,
            height=80,
            help="添加报告备注信息（可选）"
        )
        
        st.markdown("---")
        st.markdown("#### 选择报告内容")
        
        st.markdown("**📊 包含图表**")
        selected_charts = []
        for chart_id, chart_name in charts.items():
            chart_key = f"report_chart_{page_type}_{chart_id}"
            if chart_key not in st.session_state:
                st.session_state[chart_key] = True
            if st.checkbox(chart_name, key=chart_key):
                selected_charts.append(chart_id)
        
        st.markdown("**📋 包含数据表格**")
        selected_tables = []
        for table_id, table_name in tables.items():
            table_key = f"report_table_{page_type}_{table_id}"
            if table_key not in st.session_state:
                st.session_state[table_key] = True
            if st.checkbox(table_name, key=table_key):
                selected_tables.append(table_id)
        
        return {
            "title": report_title,
            "date": report_date.strftime("%Y-%m-%d"),
            "notes": report_notes,
            "charts": selected_charts,
            "tables": selected_tables
        }


def get_date_range_default():
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    return [dates[0].date(), dates[-1].date()]

def get_ticket_date_range_default():
    today = pd.Timestamp.now().date()
    start = today - pd.Timedelta(days=90)
    end = today + pd.Timedelta(days=90)
    return [start, end]

def render_sidebar(current_page=None):
    filters = {}
    
    for section in SIDEBAR_CONFIG["sections"]:
        if section.get("page_only") and section.get("page_only") != current_page:
            continue
        
        if section.get("title"):
            st.header(section["title"])
        
        for control in section["controls"]:
            control_id = control["id"]
            control_type = control["type"]
            
            if control_type == "info":
                st.info(control["content"])
                continue
            
            if control_type == "date_input":
                if control["data_source"] == "date_range":
                    if control_id == "ticket_date_range":
                        default_value = get_ticket_date_range_default()
                    else:
                        default_value = get_date_range_default()
                filters[control_id] = st.date_input(
                    control["label"],
                    value=default_value,
                    help=control.get("help")
                )
            
            elif control_type == "multiselect":
                options = control["options"]
                default = options if control.get("default") == "all" else control.get("default", [])
                filters[control_id] = st.multiselect(
                    control["label"],
                    options=options,
                    default=default,
                    help=control.get("help")
                )
            
            elif control_type == "text_input":
                filters[control_id] = st.text_input(
                    control["label"],
                    help=control.get("help")
                )
        
        if section != SIDEBAR_CONFIG["sections"][-1]:
            st.markdown("---")
    
    return filters


def render_sidebar_notification_center():
    st.markdown("---")
    unread_count = get_unread_count()
    with st.expander(f"🔔 通知中心 ({unread_count} 未读)", expanded=(unread_count > 0)):
        unread = get_notifications(limit=10, unread_only=True)
        all_notifs = get_notifications(limit=10)
        
        if not all_notifs:
            st.info("暂无通知")
        else:
            tab_unread, tab_all = st.tabs([f"未读 ({len(unread)})", "全部"])
            
            with tab_unread:
                if not unread:
                    st.info("没有未读通知")
                else:
                    for notif in unread:
                        _render_sidebar_notification_item(notif, prefix="sb_unread")
            
            with tab_all:
                for notif in all_notifs:
                    _render_sidebar_notification_item(notif, prefix="sb_all")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ 全部已读", use_container_width=True, key="sb_mark_all_read"):
                    mark_all_as_read()
                    st.rerun()
            with col2:
                if st.button("🗑️ 清空", use_container_width=True, key="sb_clear_all"):
                    clear_all_notifications()
                    st.rerun()
            
            st.markdown("---")
            st.page_link("pages/通知设置.py", label="⚙️ 通知设置", use_container_width=True)


def _render_sidebar_notification_item(notification, prefix="sb"):
    severity = notification.get("severity", "info")
    sev_info = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["info"])
    is_read = notification.get("read", False)
    bg_opacity = "0.05" if is_read else "0.1"
    
    st.markdown(
        f"""
        <div style="
            padding: 0.4rem 0.6rem;
            margin-bottom: 0.4rem;
            border-radius: 0.4rem;
            background-color: {sev_info['color']}{bg_opacity};
            border-left: 3px solid {sev_info['color']};
            opacity: {0.6 if is_read else 1.0};
        ">
            <div style="font-weight: bold; font-size: 0.8rem;">
                {sev_info['icon']} {notification['rule_name']}
            </div>
            <div style="font-size: 0.75rem; margin-top: 0.2rem;">
                {notification['message']}
            </div>
            <div style="font-size: 0.65rem; color: #888; margin-top: 0.2rem;">
                {notification['created_at']}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_read, col_del = st.columns([1, 1])
    with col_read:
        if not is_read:
            if st.button("✓ 已读", key=f"{prefix}_read_{notification['id']}", use_container_width=True):
                mark_as_read(notification["id"])
                st.rerun()
    with col_del:
        if st.button("🗑️", key=f"{prefix}_del_{notification['id']}", use_container_width=True):
            delete_notification(notification["id"])
            st.rerun()
    
    if notification.get("details") and notification["details"]:
        with st.expander("详情", expanded=False):
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
