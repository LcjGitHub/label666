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
from sidebar_config import SIDEBAR_CONFIG, render_sidebar
from ticket_utils import (
    create_ticket_from_feedback,
    is_feedback_converted,
    get_ticket_by_feedback,
    TICKET_PRIORITIES,
    DEFAULT_ASSIGNEES
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
st.markdown("---")

type_counts = feedback_df["反馈类型"].value_counts().reindex(feedback_types).fillna(0).astype(int).tolist()
total_count = len(feedback_df)
pending_count = int(total_count * 0.21)

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
df = pd.DataFrame({
    '反馈类型': feedback_types,
    '数量': type_counts,
    '占比': [f"{c/sum_counts*100:.1f}%" for c in type_counts],
    '优先级': ['高', '中', '高', '紧急', '低', '低']
})

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

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
