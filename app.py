import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_utils import (
    generate_mock_feedback_data,
    generate_feedback_summary_data,
    filter_by_date,
    filter_by_feedback_type
)
from sidebar_config import SIDEBAR_CONFIG, render_sidebar, render_report_export_section
from ticket_utils import (
    create_ticket_from_feedback,
    is_feedback_converted,
    get_ticket_by_feedback,
    TICKET_PRIORITIES,
    DEFAULT_ASSIGNEES
)
from report_utils import (
    create_pdf_report,
    create_excel_report,
    convert_figure_to_image,
    get_available_items
)

st.set_page_config(
    page_title="用户反馈分析",
    page_icon="📊",
    layout="wide"
)

feedback_df = generate_mock_feedback_data()
feedback_types, counts, daily_df, satisfaction, satisfaction_counts = generate_feedback_summary_data()

with st.sidebar:
    filters = render_sidebar(current_page="feedback")

if filters.get("date_range") and len(filters["date_range"]) == 2:
    feedback_df = filter_by_date(feedback_df, "日期", filters["date_range"][0], filters["date_range"][1])
    daily_df = filter_by_date(daily_df, "日期", filters["date_range"][0], filters["date_range"][1])

if filters.get("feedback_type"):
    feedback_df = filter_by_feedback_type(feedback_df, "反馈类型", filters["feedback_type"])

st.title("📊 用户反馈分析面板")

report_config = render_report_export_section("feedback")

if "show_report_preview" not in st.session_state:
    st.session_state.show_report_preview = False

col_preview, col_export_pdf, col_export_excel = st.columns([1, 1, 1])
with col_preview:
    if st.button("👁️ 报告预览", use_container_width=True, type="secondary"):
        st.session_state.show_report_preview = not st.session_state.show_report_preview

st.markdown("---")

type_counts = feedback_df["反馈类型"].value_counts().reindex(feedback_types).fillna(0).astype(int).tolist()
total_count = len(feedback_df)
pending_count = int(total_count * 0.21)

key_metrics = [
    {"label": "总反馈数", "value": total_count, "delta": "+12%"},
    {"label": "待处理", "value": pending_count, "delta": "-5%"},
    {"label": "平均响应时间", "value": "2.3 小时", "delta": "-0.5 小时"}
]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="总反馈数",
        value=total_count,
        delta="+12%"
    )

with col2:
    st.metric(
        label="待处理",
        value=pending_count,
        delta="-5%",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="平均响应时间",
        value="2.3 小时",
        delta="-0.5 小时",
        delta_color="normal"
    )

st.markdown("---")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("🔔 反馈类型分布")
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=feedback_types,
        values=type_counts,
        hole=0.4,
        marker=dict(
            colors=[
                '#636EFA',
                '#EF553B',
                '#00CC96',
                '#AB63FA',
                '#FFA15A',
                '#19D3F3'
            ]
        ),
        textinfo='label+percent',
        hoverinfo='label+value+percent',
        pull=[0.05, 0, 0, 0.05, 0, 0]
    )])
    
    fig_donut.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)

with col_chart2:
    st.subheader("📈 每日反馈趋势")
    
    fig_line = go.Figure()
    
    fig_line.add_trace(go.Scatter(
        x=daily_df['日期'],
        y=daily_df['反馈数量'],
        mode='lines+markers',
        name='反馈数量',
        line=dict(color='#636EFA', width=3),
        marker=dict(size=8)
    ))
    
    fig_line.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis_title="日期",
        yaxis_title="反馈数量",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")
st.subheader("😊 用户满意度分布")

fig_bar = go.Figure()

fig_bar.add_trace(go.Bar(
    x=satisfaction,
    y=satisfaction_counts,
    marker_color=[
        '#00CC96',
        '#636EFA',
        '#FFA15A',
        '#EF553B',
        '#AB63FA'
    ],
    text=satisfaction_counts,
    textposition='auto'
))

fig_bar.update_layout(
    height=400,
    margin=dict(t=50, b=50, l=50, r=50),
    xaxis_title="满意度等级",
    yaxis_title="用户数量",
    showlegend=False
)

st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
st.subheader("📋 反馈类型详细数据")

sum_counts = sum(type_counts) if sum(type_counts) > 0 else 1
df_summary = pd.DataFrame({
    '反馈类型': feedback_types,
    '数量': type_counts,
    '占比': [f"{c/sum_counts*100:.1f}%" for c in type_counts],
    '优先级': ['高', '中', '高', '紧急', '低', '低']
})

st.dataframe(
    df_summary,
    use_container_width=True,
    hide_index=True
)

chart_images = {}
if report_config["charts"]:
    if "type_distribution" in report_config["charts"]:
        chart_images["type_distribution"] = convert_figure_to_image(fig_donut)
    if "daily_trend" in report_config["charts"]:
        chart_images["daily_trend"] = convert_figure_to_image(fig_line)
    if "satisfaction" in report_config["charts"]:
        chart_images["satisfaction"] = convert_figure_to_image(fig_bar)

data_frames = {}
if report_config["tables"]:
    if "type_summary" in report_config["tables"]:
        data_frames["type_summary"] = df_summary
    if "feedback_detail" in report_config["tables"]:
        display_detail = feedback_df.copy()
        display_detail['日期'] = pd.to_datetime(display_detail['日期']).dt.strftime('%Y-%m-%d')
        data_frames["feedback_detail"] = display_detail[['反馈ID', '日期', '反馈类型', '反馈内容']]

pdf_buffer = None
excel_buffer = None
if report_config["charts"] or report_config["tables"]:
    pdf_buffer = create_pdf_report(
        report_title=report_config["title"],
        report_date=report_config["date"],
        report_notes=report_config["notes"],
        page_type="feedback",
        selected_charts=report_config["charts"],
        selected_tables=report_config["tables"],
        chart_images=chart_images,
        data_frames=data_frames,
        key_metrics=key_metrics
    )
    excel_buffer = create_excel_report(
        report_title=report_config["title"],
        report_date=report_config["date"],
        report_notes=report_config["notes"],
        page_type="feedback",
        selected_charts=report_config["charts"],
        selected_tables=report_config["tables"],
        chart_images=chart_images,
        data_frames=data_frames,
        key_metrics=key_metrics
    )

if st.session_state.show_report_preview:
    st.markdown("---")
    st.subheader("📄 报告预览")
    
    with st.container():
        col_pdf, col_excel = st.columns(2)
        with col_pdf:
            if pdf_buffer:
                st.download_button(
                    label="📥 导出 PDF",
                    data=pdf_buffer,
                    file_name=f"{report_config['title']}_{report_config['date']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.info("请至少选择一个图表或数据表格")
        
        with col_excel:
            if excel_buffer:
                st.download_button(
                    label="📊 导出 Excel",
                    data=excel_buffer,
                    file_name=f"{report_config['title']}_{report_config['date']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
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
        metric_cols = st.columns(len(key_metrics))
        for i, metric in enumerate(key_metrics):
            with metric_cols[i]:
                st.metric(label=metric['label'], value=metric['value'], delta=metric['delta'])
        
        chart_names, table_names = get_available_items("feedback")
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

st.markdown("---")
st.subheader("📑 详细反馈列表")

display_df = feedback_df.copy()
display_df['日期'] = pd.to_datetime(display_df['日期']).dt.strftime('%Y-%m-%d')

for idx, row in display_df.iterrows():
    fb_id = row['反馈ID']
    converted = is_feedback_converted(fb_id)
    ticket = get_ticket_by_feedback(fb_id) if converted else None
    
    with st.container():
        col_info, col_action = st.columns([4, 1])
        
        with col_info:
            st.markdown(f"**{row['反馈类型']}** · {row['日期']} · `{fb_id}`")
            st.write(row['反馈内容'])
            if converted and ticket:
                st.success(f"✅ 已转为工单: [{ticket['ticket_id']}](/工单管理) - 状态: **{ticket['status']}**")
        
        with col_action:
            if not converted:
                if st.button("🎫 转为工单", key=f"convert_{fb_id}", use_container_width=True):
                    st.session_state[f"show_form_{fb_id}"] = True
            else:
                if st.button("📋 查看工单", key=f"view_{fb_id}", use_container_width=True):
                    st.session_state[f"show_detail_{fb_id}"] = True
        
        if st.session_state.get(f"show_form_{fb_id}", False):
            with st.form(key=f"ticket_form_{fb_id}"):
                st.markdown(f"**创建工单 - {fb_id}**")
                st.info(f"反馈内容: {row['反馈内容']}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    assignee = st.selectbox("处理人", DEFAULT_ASSIGNEES, index=len(DEFAULT_ASSIGNEES)-1)
                    priority = st.selectbox("优先级", TICKET_PRIORITIES, index=1)
                with col_b:
                    default_due = (datetime.now() + timedelta(days=7)).date()
                    due_date = st.date_input("截止日期", value=default_due)
                    notes = st.text_area("备注信息", height=80)
                
                col_submit, col_cancel = st.columns(2)
                with col_submit:
                    submitted = st.form_submit_button("✅ 创建工单", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("❌ 取消", use_container_width=True):
                        st.session_state[f"show_form_{fb_id}"] = False
                        st.rerun()
                
                if submitted:
                    ticket = create_ticket_from_feedback(
                        feedback_id=fb_id,
                        feedback_content=row['反馈内容'],
                        feedback_type=row['反馈类型'],
                        assignee=assignee,
                        priority=priority,
                        due_date=due_date.strftime("%Y-%m-%d"),
                        notes=notes
                    )
                    st.success(f"工单 {ticket['ticket_id']} 创建成功！前往 [工单管理](/工单管理) 查看")
                    st.session_state[f"show_form_{fb_id}"] = False
        
        if st.session_state.get(f"show_detail_{fb_id}", False) and ticket:
            with st.expander(f"工单详情 - {ticket['ticket_id']}", expanded=True):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"**状态**: :blue[{ticket['status']}]")
                    st.markdown(f"**优先级**: :orange[{ticket['priority']}]")
                    st.markdown(f"**创建时间**: {ticket['created_at']}")
                with col_d2:
                    st.markdown(f"**处理人**: {ticket['assignee']}")
                    st.markdown(f"**截止日期**: {ticket['due_date']}")
                    st.markdown(f"**更新时间**: {ticket['updated_at']}")
                if ticket.get('notes'):
                    st.markdown("**备注信息**:")
                    st.info(ticket['notes'])
                if st.button("关闭详情", key=f"close_detail_{fb_id}"):
                    st.session_state[f"show_detail_{fb_id}"] = False
                    st.rerun()
        
        st.markdown("---")
