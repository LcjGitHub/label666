import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sidebar_config import render_sidebar
from ticket_utils import (
    load_tickets,
    save_tickets,
    get_ticket,
    update_ticket,
    delete_ticket,
    add_ticket_note,
    filter_tickets,
    tickets_to_dataframe,
    get_ticket_statistics,
    get_available_status_transitions,
    TICKET_STATUSES,
    TICKET_PRIORITIES,
    DEFAULT_ASSIGNEES,
    STATUS_COLOR_MAP,
    PRIORITY_COLOR_MAP
)

st.set_page_config(
    page_title="工单管理",
    page_icon="🎫",
    layout="wide"
)

with st.sidebar:
    filters = render_sidebar(current_page="tickets")

if "current_view" not in st.session_state:
    st.session_state.current_view = "list"
if "selected_ticket_id" not in st.session_state:
    st.session_state.selected_ticket_id = None


def render_ticket_list():
    st.title("🎫 工单管理")
    st.markdown("---")

    all_tickets = load_tickets()
    
    search_keyword = filters.get("ticket_search") or None
    status_filter = filters.get("ticket_status")
    priority_filter = filters.get("ticket_priority")
    assignee_filter = filters.get("ticket_assignee")
    date_filter = filters.get("ticket_date_range")
    
    date_from = None
    date_to = None
    if date_filter and len(date_filter) == 2:
        date_from = date_filter[0]
        date_to = date_filter[1]
        if date_from.year < 2025 and date_to.year < 2025:
            date_from = None
            date_to = None
    
    filtered_tickets = filter_tickets(
        all_tickets,
        status=status_filter,
        priority=priority_filter,
        assignee=assignee_filter,
        date_from=date_from,
        date_to=date_to,
        search_keyword=search_keyword
    )
    
    stats = get_ticket_statistics(filtered_tickets)
    all_stats = get_ticket_statistics(all_tickets)
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("总工单数", all_stats["total"])
    with col2:
        st.metric("待处理", stats["pending"], delta_color="off")
    with col3:
        st.metric("处理中", stats["processing"], delta_color="off")
    with col4:
        st.metric("已解决", stats["resolved"], delta_color="off")
    with col5:
        st.metric("已关闭", stats["closed"], delta_color="off")
    with col6:
        overdue_delta = f"{stats['overdue']} 个逾期" if stats["overdue"] > 0 else "正常"
        st.metric("逾期工单", stats["overdue"], delta=overdue_delta,
                  delta_color="inverse" if stats["overdue"] > 0 else "normal")

    st.markdown("---")
    st.subheader(f"📋 工单列表 ({len(filtered_tickets)} 条)")

    if not filtered_tickets:
        if len(all_tickets) > 0:
            st.warning(f"当前筛选条件下没有工单，系统中共有 {len(all_tickets)} 个工单。请尝试调整筛选条件。")
            if st.button("🔄 清除所有筛选条件"):
                for key in st.session_state.keys():
                    if key.startswith("filter_"):
                        del st.session_state[key]
                st.rerun()
        else:
            st.info("暂无工单数据。请在反馈分析页面将反馈转换为工单。")
        return

    df = tickets_to_dataframe(filtered_tickets)
    df = df.sort_values("创建时间", ascending=False)

    def color_status(val):
        color = STATUS_COLOR_MAP.get(val, "#888")
        return f"background-color: {color}; color: white; border-radius: 4px; padding: 2px 8px; text-align: center;"

    def color_priority(val):
        color = PRIORITY_COLOR_MAP.get(val, "#888")
        return f"background-color: {color}; color: white; border-radius: 4px; padding: 2px 8px; text-align: center;"

    styled_df = df.style.map(color_status, subset=["状态"]).map(color_priority, subset=["优先级"])

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "工单编号": st.column_config.TextColumn("工单编号", width="medium"),
            "标题": st.column_config.TextColumn("标题", width="large"),
            "状态": st.column_config.TextColumn("状态", width="small"),
            "优先级": st.column_config.TextColumn("优先级", width="small"),
            "处理人": st.column_config.TextColumn("处理人", width="small"),
            "创建时间": st.column_config.TextColumn("创建时间", width="medium"),
            "截止日期": st.column_config.TextColumn("截止日期", width="medium"),
            "反馈类型": st.column_config.TextColumn("反馈类型", width="small")
        }
    )

    st.markdown("---")
    st.subheader("🔧 工单操作")
    st.write("选择工单进行查看详情或操作：")

    ticket_options = [f"{t['ticket_id']} - {t['title']}" for t in filtered_tickets]
    ticket_ids = [t["ticket_id"] for t in filtered_tickets]

    selected_idx = st.selectbox(
        "选择工单",
        range(len(ticket_options)),
        format_func=lambda i: ticket_options[i]
    )

    col_view, col_delete = st.columns(2)
    with col_view:
        if st.button("📄 查看详情", use_container_width=True, type="primary"):
            st.session_state.selected_ticket_id = ticket_ids[selected_idx]
            st.session_state.current_view = "detail"
            st.rerun()
    with col_delete:
        if st.button("🗑️ 删除工单", use_container_width=True):
            if st.session_state.get(f"confirm_delete_{ticket_ids[selected_idx]}", False):
                delete_ticket(ticket_ids[selected_idx])
                st.success(f"工单 {ticket_ids[selected_idx]} 已删除")
                st.rerun()
            else:
                st.session_state[f"confirm_delete_{ticket_ids[selected_idx]}"] = True
                st.warning("⚠️ 再次点击删除按钮确认删除此工单")


def render_ticket_detail():
    ticket_id = st.session_state.selected_ticket_id
    ticket = get_ticket(ticket_id)

    if not ticket:
        st.error(f"工单 {ticket_id} 不存在")
        if st.button("← 返回工单列表"):
            st.session_state.current_view = "list"
            st.session_state.selected_ticket_id = None
            st.rerun()
        return

    st.title(f"🎫 工单详情 - {ticket_id}")
    st.markdown("---")

    col_back, col_status, col_priority = st.columns([1, 2, 2])
    with col_back:
        if st.button("← 返回列表", use_container_width=True):
            st.session_state.current_view = "list"
            st.session_state.selected_ticket_id = None
            st.rerun()

    st.markdown("---")

    col_info1, col_info2 = st.columns(2)

    with col_info1:
        st.subheader("📋 基本信息")
        st.markdown(f"**工单编号**: `{ticket['ticket_id']}`")
        st.markdown(f"**关联反馈ID**: `{ticket.get('feedback_id', 'N/A')}`")
        st.markdown(f"**反馈类型**: {ticket['feedback_type']}")
        st.markdown(f"**标题**: {ticket['title']}")
        st.markdown("**反馈内容**:")
        st.info(ticket['feedback_content'])

    with col_info2:
        st.subheader("⚙️ 工单属性")

        with st.form("update_ticket_form"):
            new_status = st.selectbox(
                "状态",
                TICKET_STATUSES,
                index=TICKET_STATUSES.index(ticket['status'])
            )

            available_transitions = get_available_status_transitions(ticket['status'])
            if available_transitions:
                st.caption(f"可流转状态: {', '.join(available_transitions)}")
            else:
                st.caption("当前状态不可再流转")

            new_assignee = st.selectbox(
                "处理人",
                DEFAULT_ASSIGNEES,
                index=DEFAULT_ASSIGNEES.index(ticket['assignee']) if ticket['assignee'] in DEFAULT_ASSIGNEES else len(DEFAULT_ASSIGNEES) - 1
            )

            new_priority = st.selectbox(
                "优先级",
                TICKET_PRIORITIES,
                index=TICKET_PRIORITIES.index(ticket['priority'])
            )

            try:
                current_due = datetime.strptime(ticket['due_date'], "%Y-%m-%d").date()
            except ValueError:
                current_due = (datetime.now() + timedelta(days=7)).date()
            new_due = st.date_input("截止日期", value=current_due)

            submitted = st.form_submit_button("💾 更新工单", type="primary", use_container_width=True)

            if submitted:
                update_ticket(
                    ticket_id,
                    status=new_status,
                    assignee=new_assignee,
                    priority=new_priority,
                    due_date=new_due.strftime("%Y-%m-%d")
                )
                st.success("✅ 工单信息已更新！")
                st.rerun()

    st.markdown("---")
    col_status2, col_dates = st.columns(2)
    with col_status2:
        st.markdown(f"**当前状态**: :{_get_status_color(ticket['status'])}[{ticket['status']}]")
        st.markdown(f"**优先级**: :{_get_priority_color(ticket['priority'])}[{ticket['priority']}]")
        st.markdown(f"**处理人**: **{ticket['assignee']}**")
    with col_dates:
        st.markdown(f"**创建时间**: {ticket['created_at']}")
        st.markdown(f"**更新时间**: {ticket['updated_at']}")
        st.markdown(f"**截止日期**: {ticket['due_date']}")

    st.markdown("---")
    st.subheader("📝 备注信息")

    if ticket.get('notes'):
        st.markdown(ticket['notes'].replace('\n', '\n\n'))
    else:
        st.info("暂无备注信息")

    with st.form("add_note_form"):
        new_note = st.text_area("添加新备注", height=100, placeholder="在这里输入备注信息...")
        note_submitted = st.form_submit_button("✏️ 添加备注", use_container_width=True)
        if note_submitted and new_note.strip():
            add_ticket_note(ticket_id, new_note.strip())
            st.success("✅ 备注已添加！")
            st.rerun()

    st.markdown("---")
    st.subheader("📜 操作历史")

    if ticket.get('history'):
        history_df = pd.DataFrame(ticket['history'])
        history_df = history_df.sort_values("timestamp", ascending=False)
        
        for _, row in history_df.iterrows():
            with st.container():
                col_t, col_a, col_d = st.columns([2, 1, 4])
                col_t.markdown(f"🕐 {row['timestamp']}")
                col_a.markdown(f"**{row['action']}**")
                col_d.markdown(row['details'])
                st.markdown("---")
    else:
        st.info("暂无操作历史")


def _get_status_color(status):
    if status == "待处理":
        return "orange"
    elif status == "处理中":
        return "blue"
    elif status == "已解决":
        return "green"
    elif status == "已关闭":
        return "violet"
    return "gray"


def _get_priority_color(priority):
    if priority == "紧急":
        return "red"
    elif priority == "高":
        return "orange"
    elif priority == "中":
        return "blue"
    elif priority == "低":
        return "green"
    return "gray"


if __name__ == "__main__":
    if st.session_state.current_view == "detail" and st.session_state.selected_ticket_id:
        render_ticket_detail()
    else:
        render_ticket_list()
