import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from auth_utils import (
    init_session,
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    has_permission,
    require_permission,
    get_current_user
)
from sidebar_config import render_sidebar, render_report_export_section, render_sidebar_notification_center
from notification_utils import (
    init_notification_system,
    render_notification_icon,
    render_notification_popup,
    run_monitoring_checks,
    SEVERITY_LEVELS,
    load_display_config
)
from ticket_utils import (
    load_tickets,
    save_tickets,
    get_ticket,
    update_ticket,
    delete_ticket,
    add_ticket_note,
    add_ticket_comment,
    get_ticket_comments,
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
from report_utils import (
    create_pdf_report,
    create_excel_report,
    convert_figure_to_image,
    get_available_items
)

st.set_page_config(
    page_title="工单管理",
    page_icon="🎫",
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

can_export = has_permission("export_data")

with st.sidebar:
    render_user_info_in_sidebar()
    display_config = load_display_config()
    if display_config.get("show_sidebar_notification", True):
        render_sidebar_notification_center()
    filters = render_sidebar(current_page="tickets")

if "current_view" not in st.session_state:
    st.session_state.current_view = "list"
if "selected_ticket_id" not in st.session_state:
    st.session_state.selected_ticket_id = None


def render_ticket_list():
    st.title("🎫 工单管理")
    
    if has_permission("edit_config") or has_permission("export_data"):
        report_config = render_report_export_section("tickets")
    else:
        report_config = {
            "title": "工单管理报告",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "",
            "charts": [],
            "tables": []
        }
    
    if "show_report_preview_tickets" not in st.session_state:
        st.session_state.show_report_preview_tickets = False
    
    if has_permission("export_data"):
        col_preview, col_export_pdf, col_export_excel = st.columns([1, 1, 1])
        with col_preview:
            if st.button("👁️ 报告预览", use_container_width=True, type="secondary", key="ticket_preview_btn"):
                st.session_state.show_report_preview_tickets = not st.session_state.show_report_preview_tickets
    else:
        st.info("💡 提示：如需导出报告功能，请联系管理员开通「导出数据」权限。")
    
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

    if can_export:
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
    else:
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.subheader("🔧 工单操作")
    st.write("选择工单进行查看详情或操作：")

    ticket_options = [f"{t['ticket_id']} - {t['title']}" for t in filtered_tickets]
    ticket_ids = [t["ticket_id"] for t in filtered_tickets]
    can_manage_tickets = has_permission("manage_tickets")

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
        if can_manage_tickets:
            if st.button("🗑️ 删除工单", use_container_width=True):
                if st.session_state.get(f"confirm_delete_{ticket_ids[selected_idx]}", False):
                    delete_ticket(ticket_ids[selected_idx])
                    st.success(f"工单 {ticket_ids[selected_idx]} 已删除")
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{ticket_ids[selected_idx]}"] = True
                    st.warning("⚠️ 再次点击删除按钮确认删除此工单")
        else:
            st.button("🔒 删除工单", use_container_width=True, disabled=True)
    
    key_metrics = [
        {"label": "总工单数", "value": all_stats["total"], "delta": "全部工单"},
        {"label": "待处理", "value": stats["pending"], "delta": "待处理工单数"},
        {"label": "处理中", "value": stats["processing"], "delta": "处理中工单数"},
        {"label": "已解决", "value": stats["resolved"], "delta": "已解决工单数"},
        {"label": "已关闭", "value": stats["closed"], "delta": "已关闭工单数"},
        {"label": "逾期工单", "value": stats["overdue"], "delta": "逾期工单数"}
    ]
    
    chart_images = {}
    fig_status = None
    fig_priority = None
    
    if report_config["charts"]:
        if "ticket_status" in report_config["charts"]:
            status_labels = TICKET_STATUSES
            status_values = [stats["pending"], stats["processing"], stats["resolved"], stats["closed"]]
            
            fig_status = go.Figure(data=[go.Pie(
                labels=status_labels,
                values=status_values,
                hole=0.4,
                marker=dict(
                    colors=[STATUS_COLOR_MAP[s] for s in status_labels]
                ),
                textinfo='label+percent',
                hoverinfo='label+value+percent'
            )])
            fig_status.update_layout(
                title="工单状态分布",
                height=400,
                margin=dict(t=50, b=50, l=50, r=50)
            )
            chart_images["ticket_status"] = convert_figure_to_image(fig_status)
        
        if "ticket_priority" in report_config["charts"]:
            priority_labels = TICKET_PRIORITIES
            priority_counts = {}
            for p in priority_labels:
                priority_counts[p] = len([t for t in filtered_tickets if t["priority"] == p])
            priority_values = [priority_counts[p] for p in priority_labels]
            
            fig_priority = go.Figure()
            fig_priority.add_trace(go.Bar(
                x=priority_labels,
                y=priority_values,
                marker_color=[PRIORITY_COLOR_MAP[p] for p in priority_labels],
                text=priority_values,
                textposition='auto'
            ))
            fig_priority.update_layout(
                title="工单优先级分布",
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                xaxis_title="优先级",
                yaxis_title="工单数量",
                showlegend=False)
            chart_images["ticket_priority"] = convert_figure_to_image(fig_priority)
    
    df_ticket_summary = pd.DataFrame({
        '指标': ['总工单数', '待处理', '处理中', '已解决', '已关闭', '逾期工单'],
        '数量': [all_stats["total"], stats["pending"], stats["processing"], stats["resolved"], stats["closed"], stats["overdue"]]
    })
    
    data_frames = {}
    if report_config["tables"]:
        if "ticket_summary" in report_config["tables"]:
            data_frames["ticket_summary"] = df_ticket_summary
        if "ticket_detail" in report_config["tables"]:
            data_frames["ticket_detail"] = df
    
    ticket_pdf_buffer = None
    ticket_excel_buffer = None
    if report_config["charts"] or report_config["tables"]:
        ticket_pdf_buffer = create_pdf_report(
            report_title=report_config["title"],
            report_date=report_config["date"],
            report_notes=report_config["notes"],
            page_type="tickets",
            selected_charts=report_config["charts"],
            selected_tables=report_config["tables"],
            chart_images=chart_images,
            data_frames=data_frames,
            key_metrics=key_metrics
        )
        ticket_excel_buffer = create_excel_report(
            report_title=report_config["title"],
            report_date=report_config["date"],
            report_notes=report_config["notes"],
            page_type="tickets",
            selected_charts=report_config["charts"],
            selected_tables=report_config["tables"],
            chart_images=chart_images,
            data_frames=data_frames,
            key_metrics=key_metrics
        )
    
    if has_permission("export_data") and st.session_state.show_report_preview_tickets:
        st.markdown("---")
        st.subheader("📄 报告预览")
        
        with st.container():
            col_pdf, col_excel = st.columns(2)
            with col_pdf:
                if ticket_pdf_buffer:
                    st.download_button(
                        label="📥 导出 PDF",
                        data=ticket_pdf_buffer,
                        file_name=f"{report_config['title']}_{report_config['date']}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                        key="ticket_pdf_download"
                    )
                else:
                    st.info("请至少选择一个图表或数据表格")
            
            with col_excel:
                if ticket_excel_buffer:
                    st.download_button(
                        label="📊 导出 Excel",
                        data=ticket_excel_buffer,
                        file_name=f"{report_config['title']}_{report_config['date']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary",
                        key="ticket_excel_download"
                    )
                else:
                    st.info("请至少选择一个图表或数据表格")
            
            st.markdown("---")
            st.markdown("### 报告基本信息")
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.markdown(f"- **报告标题**: {report_config['title']}")
                st.markdown(f"- **报告日期**: {report_config['date']}")
            with info_col2:
                if report_config["notes"]:
                    st.markdown(f"- **备注信息**: {report_config['notes']}")
            
            st.markdown("---")
            st.markdown("### 关键指标摘要")
            metric_cols = st.columns(min(len(key_metrics), 3))
            for i, metric in enumerate(key_metrics):
                with metric_cols[i % 3]:
                    st.metric(label=metric['label'], value=metric['value'], delta=metric['delta'])
            
            chart_names, table_names = get_available_items("tickets")
            if report_config["charts"] and chart_images:
                st.markdown("---")
                st.markdown("### 图表预览")
                num_charts = len(report_config["charts"])
                chart_cols = st.columns(min(num_charts, 2))
                for i, chart_id in enumerate(report_config["charts"]):
                    if chart_id in chart_images and chart_images[chart_id]:
                        col_idx = i % 2
                        with chart_cols[col_idx]:
                            st.markdown(f"**{chart_names.get(chart_id, chart_id)}**")
                            img_data = chart_images[chart_id]
                            if hasattr(img_data, 'seek'):
                                img_data.seek(0)
                            st.image(img_data, use_column_width=True)
                            if (i + 1) % 2 == 0 and i < num_charts - 1:
                                st.markdown("---")
            
            if report_config["tables"] and data_frames:
                st.markdown("---")
                st.markdown("### 数据表格预览")
                for table_id in report_config["tables"]:
                    if table_id in data_frames and data_frames[table_id] is not None:
                        df = data_frames[table_id]
                        if not df.empty:
                            st.markdown(f"**{table_names.get(table_id, table_id)}**")
                            preview_df = df.head(5)
                            st.dataframe(preview_df, use_container_width=True, hide_index=True)
                            if len(df) > 5:
                                st.caption(f"共 {len(df)} 条数据，仅显示前 5 条")
                            st.markdown("---")


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
        can_manage_tickets = has_permission("manage_tickets")

        if can_manage_tickets:
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
        else:
            st.info("🔒 您没有「管理工单」权限，无法修改工单属性。")
            st.markdown(f"**状态**: {ticket['status']}")
            st.markdown(f"**处理人**: {ticket['assignee']}")
            st.markdown(f"**优先级**: {ticket['priority']}")
            st.markdown(f"**截止日期**: {ticket['due_date']}")

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

    if can_manage_tickets:
        with st.form("add_note_form"):
            new_note = st.text_area("添加新备注", height=100, placeholder="在这里输入备注信息...")
            note_submitted = st.form_submit_button("✏️ 添加备注", use_container_width=True)
            if note_submitted and new_note.strip():
                add_ticket_note(ticket_id, new_note.strip())
                st.success("✅ 备注已添加！")
                st.rerun()
    else:
        st.info("🔒 您没有「管理工单」权限，无法添加备注。")

    st.markdown("---")
    st.subheader("💬 工单评论")

    comments = get_ticket_comments(ticket_id)
    if comments:
        for comment in comments:
            with st.container():
                col_user, col_time = st.columns([2, 3])
                col_user.markdown(f"**👤 {comment['commenter']}**")
                col_time.markdown(f"🕐 {comment['created_at']}")
                st.markdown(comment['content'].replace('\n', '\n\n'))
                st.markdown("---")
    else:
        st.info("暂无评论记录")

    if can_manage_tickets:
        current_user = get_current_user()
        commenter_name = current_user.get("full_name", current_user.get("username", "未知用户")) if current_user else "未知用户"
        with st.form("add_comment_form"):
            st.markdown(f"**评论人**: {commenter_name}")
            new_comment = st.text_area(
                "添加评论",
                height=120,
                placeholder="在这里输入评论内容，记录本次沟通的详细信息..."
            )
            comment_submitted = st.form_submit_button("💬 发布评论", use_container_width=True, type="primary")
            if comment_submitted:
                if not new_comment.strip():
                    st.error("请输入评论内容")
                else:
                    add_ticket_comment(ticket_id, commenter_name, new_comment.strip())
                    st.success("✅ 评论已发布！")
                    st.rerun()
    else:
        st.info("🔒 您没有「管理工单」权限，无法添加评论。")

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
