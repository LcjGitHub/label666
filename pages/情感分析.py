import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from data_utils import (
    generate_mock_feedback_data,
    filter_by_date,
    filter_by_feedback_type,
    filter_by_sentiment,
    extract_keywords,
    create_wordcloud
)
from sidebar_config import render_sidebar

st.set_page_config(
    page_title="情感分析",
    page_icon="💭",
    layout="wide"
)

feedback_df = generate_mock_feedback_data()

with st.sidebar:
    filters = render_sidebar(current_page="sentiment")

if filters.get("date_range") and len(filters["date_range"]) == 2:
    feedback_df = filter_by_date(feedback_df, "日期", filters["date_range"][0], filters["date_range"][1])

if filters.get("feedback_type"):
    feedback_df = filter_by_feedback_type(feedback_df, "反馈类型", filters["feedback_type"])

if filters.get("sentiment_type"):
    feedback_df = filter_by_sentiment(feedback_df, "情感类别", filters["sentiment_type"])

st.title("💭 情感分析面板")
st.markdown("---")

total_count = len(feedback_df)
pos_count = len(feedback_df[feedback_df['情感类别'] == '正面'])
neu_count = len(feedback_df[feedback_df['情感类别'] == '中性'])
neg_count = len(feedback_df[feedback_df['情感类别'] == '负面'])

pos_pct = f"{pos_count/total_count*100:.1f}%" if total_count > 0 else "0%"
neu_pct = f"{neu_count/total_count*100:.1f}%" if total_count > 0 else "0%"
neg_pct = f"{neg_count/total_count*100:.1f}%" if total_count > 0 else "0%"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="总反馈数",
        value=total_count
    )

with col2:
    st.metric(
        label="😊 正面反馈",
        value=f"{pos_count}",
        delta=pos_pct,
        delta_color="normal"
    )

with col3:
    st.metric(
        label="😐 中性反馈",
        value=f"{neu_count}",
        delta=neu_pct,
        delta_color="off"
    )

with col4:
    st.metric(
        label="😞 负面反馈",
        value=f"{neg_count}",
        delta=neg_pct,
        delta_color="inverse"
    )

st.markdown("---")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("🥧 情感占比分布")
    
    sentiment_labels = ['正面', '中性', '负面']
    sentiment_values = [pos_count, neu_count, neg_count]
    sentiment_colors = ['#00CC96', '#FFA15A', '#EF553B']
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=sentiment_labels,
        values=sentiment_values,
        hole=0.4,
        marker=dict(
            colors=sentiment_colors
        ),
        textinfo='label+percent',
        hoverinfo='label+value+percent',
        pull=[0.05, 0, 0.05]
    )])
    
    fig_pie.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    st.subheader("📉 情感变化趋势（按周聚合）")
    
    weekly_sentiment = feedback_df.groupby([
        pd.Grouper(key='日期', freq='W-MON'),
        '情感类别'
    ]).size().unstack(fill_value=0)
    
    for col in ['正面', '中性', '负面']:
        if col not in weekly_sentiment.columns:
            weekly_sentiment[col] = 0
    
    weekly_sentiment = weekly_sentiment[['正面', '中性', '负面']]
    
    fig_trend = go.Figure()
    
    color_map = {'正面': '#00CC96', '中性': '#FFA15A', '负面': '#EF553B'}
    
    for sentiment in weekly_sentiment.columns:
        fig_trend.add_trace(go.Scatter(
            x=weekly_sentiment.index.strftime('%Y-%m-%d'),
            y=weekly_sentiment[sentiment],
            mode='lines+markers',
            name=sentiment,
            line=dict(color=color_map[sentiment], width=3),
            marker=dict(size=9)
        ))
    
    fig_trend.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis_title="周起始日期",
        yaxis_title="反馈数量",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")
st.subheader("☁️ 反馈关键词词云")

word_freq = extract_keywords(feedback_df['反馈内容'].tolist())

if word_freq:
    col_wc1, col_wc2 = st.columns([2, 1])
    
    with col_wc1:
        wc_img = create_wordcloud(word_freq)
        if wc_img:
            st.image(wc_img, use_container_width=True, caption='用户反馈高频关键词词云')
    
    with col_wc2:
        st.markdown("#### 🔝 Top 15 关键词")
        
        top_words = word_freq[:15]
        words_df = pd.DataFrame(top_words, columns=['关键词', '出现次数'])
        words_df.index = range(1, len(words_df) + 1)
        
        st.dataframe(
            words_df,
            use_container_width=True,
            height=400
        )
else:
    st.warning("暂无足够的文本数据生成词云")

st.markdown("---")
st.subheader("📋 情感分析详细数据")

display_df = feedback_df.copy()
display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')

sentiment_emoji = {
    '正面': '😊 正面',
    '中性': '😐 中性',
    '负面': '😞 负面'
}
display_df['情感类别'] = display_df['情感类别'].map(sentiment_emoji)

st.dataframe(
    display_df[['日期', '反馈类型', '情感类别', '情感强度', '反馈内容']],
    use_container_width=True,
    hide_index=True,
    column_config={
        "反馈内容": st.column_config.TextColumn(
            "反馈内容",
            width="large"
        )
    }
)
