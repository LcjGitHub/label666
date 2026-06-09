import streamlit as st
import pandas as pd
from datetime import datetime
from report_utils import get_available_items

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
            "id": "report_export",
            "title": "📤 报告导出",
            "expanded": False,
            "controls": [
                {
                    "id": "report_tip",
                    "type": "info",
                    "content": "点击页面顶部的「报告导出」按钮进行详细配置"
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
                    "content": "💡 提示：使用上方筛选器来过滤数据"
                }
            ]
        }
    ]
}


REPORT_DEFAULT_TITLES = {
    "feedback": "用户反馈分析报告",
    "sentiment": "情感分析报告",
    "tickets": "工单统计报告"
}


def render_report_export_section(page_type):
    charts, tables = get_available_items(page_type)
    
    with st.expander("📤 报告导出配置", expanded=False):
        st.markdown("#### 报告基本信息")
        
        default_title = REPORT_DEFAULT_TITLES.get(page_type, "分析报告")
        report_title = st.text_input(
            "报告标题",
            value=st.session_state.get(f"report_title_{page_type}", default_title),
            help="设置导出报告的标题"
        )
        st.session_state[f"report_title_{page_type}"] = report_title
        
        report_date = st.date_input(
            "报告日期",
            value=st.session_state.get(f"report_date_{page_type}", datetime.now().date()),
            help="选择报告生成日期"
        )
        st.session_state[f"report_date_{page_type}"] = report_date
        
        report_notes = st.text_area(
            "备注信息",
            value=st.session_state.get(f"report_notes_{page_type}", ""),
            height=80,
            help="添加报告备注信息（可选）"
        )
        st.session_state[f"report_notes_{page_type}"] = report_notes
        
        st.markdown("---")
        st.markdown("#### 选择报告内容")
        
        st.markdown("**📊 包含图表**")
        selected_charts = []
        for chart_id, chart_name in charts.items():
            key = f"report_chart_{page_type}_{chart_id}"
            if key not in st.session_state:
                st.session_state[key] = True
            if st.checkbox(chart_name, value=st.session_state[key], key=key):
                selected_charts.append(chart_id)
        
        st.markdown("**📋 包含数据表格**")
        selected_tables = []
        for table_id, table_name in tables.items():
            key = f"report_table_{page_type}_{table_id}"
            if key not in st.session_state:
                st.session_state[key] = True
            if st.checkbox(table_name, value=st.session_state[key], key=key):
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
