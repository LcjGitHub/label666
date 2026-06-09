import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from data_utils import (
    generate_mock_feedback_data,
    generate_feedback_summary_data,
    filter_by_date,
    filter_by_feedback_type
)
from sidebar_config import SIDEBAR_CONFIG, render_sidebar

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
display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')

st.dataframe(
    display_df[['日期', '反馈类型', '反馈内容']],
    use_container_width=True,
    hide_index=True,
    column_config={
        "反馈内容": st.column_config.TextColumn(
            "反馈内容",
            width="large"
        )
    }
)
