import streamlit as st
import pandas as pd

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
                    "content": "💡 提示：使用上方筛选器来过滤数据"
                }
            ]
        }
    ]
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
