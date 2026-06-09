import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# 页面配置
st.set_page_config(
    page_title="用户反馈分析",
    page_icon="📊",
    layout="wide"
)

# 标题
st.title("📊 用户反馈分析面板")
st.markdown("---")

# Mock 数据生成
def generate_mock_data():
    np.random.seed(42)
    
    # 反馈类型分布数据
    feedback_types = [
        "功能建议",
        "界面优化",
        "性能问题",
        "Bug 报告",
        "使用咨询",
        "其他"
    ]
    
    counts = [45, 30, 25, 60, 35, 15]
    
    # 生成时间序列数据
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    daily_feedback = np.random.randint(5, 25, size=30)
    
    # 满意度分布
    satisfaction = ["非常满意", "满意", "一般", "不满意", "非常不满意"]
    satisfaction_counts = [120, 180, 95, 45, 10]
    
    return feedback_types, counts, dates, daily_feedback, satisfaction, satisfaction_counts

# 生成数据
feedback_types, counts, dates, daily_feedback, satisfaction, satisfaction_counts = generate_mock_data()

# 创建三列布局
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="总反馈数",
        value=sum(counts),
        delta="+12%"
    )

with col2:
    st.metric(
        label="待处理",
        value=45,
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

# 创建图表区域
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("🔔 反馈类型分布")
    
    # 创建环形图
    fig_donut = go.Figure(data=[go.Pie(
        labels=feedback_types,
        values=counts,
        hole=0.4,
        marker={
            'colors': [
                '#636EFA',
                '#EF553B',
                '#00CC96',
                '#AB63FA',
                '#FFA15A',
                '#19D3F3'
            ]
        },
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
    
    # 创建折线图
    fig_line = go.Figure()
    
    fig_line.add_trace(go.Scatter(
        x=dates,
        y=daily_feedback,
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

# 满意度分布
st.markdown("---")
st.subheader("😊 用户满意度分布")

# 创建满意度柱状图
fig_bar = go.Figure()

fig_bar.add_trace(go.Bar(
    x=satisfaction,
    y=satisfaction_counts,
    marker={
        'colors': [
            '#00CC96',
            '#636EFA',
            '#FFA15A',
            '#EF553B',
            '#AB63FA'
        ]
    },
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

# 详细数据表格
st.markdown("---")
st.subheader("📋 反馈类型详细数据")

# 创建数据框
df = pd.DataFrame({
    '反馈类型': feedback_types,
    '数量': counts,
    '占比': [f"{c/sum(counts)*100:.1f}%" for c in counts],
    '优先级': ['高', '中', '高', '紧急', '低', '低']
})

# 显示数据表
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

# 侧边栏过滤器
with st.sidebar:
    st.header("🔍 筛选器")
    
    date_range = st.date_input(
        "选择日期范围",
        value=[dates[0].date(), dates[-1].date()]
    )
    
    feedback_type_filter = st.multiselect(
        "选择反馈类型",
        options=feedback_types,
        default=feedback_types
    )
    
    st.info("💡 提示：使用上方筛选器来过滤数据")
