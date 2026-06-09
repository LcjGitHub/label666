import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import jieba
from wordcloud import WordCloud
from collections import Counter
import io
from PIL import Image

st.set_page_config(
    page_title="用户反馈分析",
    page_icon="📊",
    layout="wide"
)

POSITIVE_WORDS = [
    "好", "棒", "优秀", "满意", "喜欢", "赞", "不错", "很好", "非常好",
    "完美", "出色", "厉害", "方便", "快速", "高效", "流畅", "稳定", "实用",
    "清晰", "简洁", "美观", "贴心", "智能", "人性化", "惊喜", "感谢", "支持",
    "推荐", "值得", "舒服", "顺畅", "省心", "靠谱", "专业", "及时", "热情"
]

NEGATIVE_WORDS = [
    "差", "烂", "糟糕", "失望", "讨厌", "慢", "卡", "崩溃", "报错", "失败",
    "难用", "复杂", "混乱", "麻烦", "垃圾", "垃圾", "恶心", "无语", "坑爹",
    "离谱", "垃圾", "气人", "烦人", "浪费", "骗", "虚假", "推卸", "敷衍",
    "拖沓", "低效", "卡顿", "闪退", "黑屏", "出错", "bug", "问题", "故障"
]

def analyze_sentiment(text):
    text = str(text).lower()
    pos_count = sum(1 for word in POSITIVE_WORDS if word in text)
    neg_count = sum(1 for word in NEGATIVE_WORDS if word in text)
    
    if pos_count > neg_count:
        return "正面", pos_count - neg_count
    elif neg_count > pos_count:
        return "负面", neg_count - pos_count
    else:
        return "中性", 0

def generate_mock_feedback_data():
    np.random.seed(42)
    
    feedback_texts = [
        "这个功能真的太棒了，使用起来非常方便，界面也很美观！",
        "产品整体不错，但有时候会有点卡顿，希望能优化一下性能。",
        "客服响应很及时，问题解决得很快，非常满意！",
        "新版本更新后经常崩溃，体验很差，希望尽快修复。",
        "操作流程有点复杂，新手不太容易上手，建议简化。",
        "数据分析功能很强大，帮了我很大的忙，赞一个！",
        "界面设计很简洁清晰，用起来很舒服。",
        "加载速度太慢了，等半天都打不开，太气人了。",
        "总体来说还可以，中规中矩，没有太大惊喜。",
        "导出报表功能很实用，节省了很多时间，感谢开发团队！",
        "bug太多了，经常出错，让人很失望。",
        "推荐给了同事，大家都说很好用！",
        "功能太单一了，希望能增加更多实用的功能。",
        "稳定性不错，用了几个月都没出什么问题。",
        "文档写得很清楚，遇到问题很快就解决了。",
        "价格有点贵，性价比一般般吧。",
        "移动端适配做得很好，手机上也很流畅。",
        "这次更新修复了很多问题，体验提升明显，点赞！",
        "搜索功能不太好用，经常搜不到想要的内容。",
        "团队协作功能非常实用，大大提高了工作效率！",
        "界面配色有点难看，希望能改一改。",
        "客服态度很差，问问题都敷衍了事。",
        "用了很长时间了，一直很稳定，值得信赖。",
        "功能更新太慢了，等了好久都没新功能。",
        "数据可视化效果很棒，老板看了很满意。",
        "登录经常失败，验证码也收不到，烦死了。",
        "整体体验不错，希望继续保持！",
        "操作反人类，很多功能都找不到在哪里。",
        "上手很快，教程也很详细，新手友好。",
        "上传文件经常失败，文件大小限制太小了。",
        "消息推送很及时，不会错过重要信息。",
        "页面布局有点乱，需要好好整理一下。",
        "售后服务很贴心，问题解决得很专业。",
        "运行占用内存太大了，电脑都卡了。",
        "功能很全面，基本满足所有需求。",
        "反应迟钝，点半天没反应，太低效了。",
        "安全性能做得很好，用着放心。",
        "兼容性太差，某些浏览器根本用不了。",
        "升级后体验提升很大，开发团队辛苦了！",
        "很多功能都要收费，免费版基本没法用。"
    ]
    
    dates = pd.date_range(start="2024-01-01", periods=len(feedback_texts), freq="D")
    sentiments = []
    scores = []
    
    for text in feedback_texts:
        sentiment, score = analyze_sentiment(text)
        sentiments.append(sentiment)
        scores.append(score)
    
    df = pd.DataFrame({
        '日期': dates,
        '反馈内容': feedback_texts,
        '情感类别': sentiments,
        '情感强度': scores
    })
    
    return df

def generate_mock_data():
    np.random.seed(42)
    
    feedback_types = [
        "功能建议",
        "界面优化",
        "性能问题",
        "Bug 报告",
        "使用咨询",
        "其他"
    ]
    
    counts = [45, 30, 25, 60, 35, 15]
    
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    daily_feedback = np.random.randint(5, 25, size=30)
    
    satisfaction = ["非常满意", "满意", "一般", "不满意", "非常不满意"]
    satisfaction_counts = [120, 180, 95, 45, 10]
    
    return feedback_types, counts, dates, daily_feedback, satisfaction, satisfaction_counts

def extract_keywords(texts, top_n=50):
    all_words = []
    stop_words = set([
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '他', '她', '它', '们', '这个', '那个', '什么', '怎么',
        '但', '但是', '还', '还是', '能', '可以', '太', '真的', '非常', '比较'
    ])
    
    for text in texts:
        words = jieba.cut(str(text))
        for word in words:
            word = word.strip()
            if len(word) > 1 and word not in stop_words:
                all_words.append(word)
    
    word_counts = Counter(all_words)
    return word_counts.most_common(top_n)

def create_wordcloud(word_freq):
    if not word_freq:
        return None
    
    word_dict = dict(word_freq)
    
    wc = WordCloud(
        font_path='C:/Windows/Fonts/msyh.ttc',
        width=800,
        height=400,
        background_color='white',
        max_words=100,
        colormap='viridis',
        prefer_horizontal=0.7
    )
    
    wc.generate_from_frequencies(word_dict)
    
    img = wc.to_image()
    return img

with st.sidebar:
    st.header("🎯 视图切换")
    view_mode = st.radio(
        "选择分析视图",
        options=["📊 反馈分析", "💭 情感分析"],
        index=0
    )
    
    st.markdown("---")
    st.header("🔍 筛选器")
    
    feedback_types_all = ["功能建议", "界面优化", "性能问题", "Bug 报告", "使用咨询", "其他"]
    dates_all = pd.date_range(start="2024-01-01", periods=30, freq="D")
    
    date_range = st.date_input(
        "选择日期范围",
        value=[dates_all[0].date(), dates_all[-1].date()]
    )
    
    feedback_type_filter = st.multiselect(
        "选择反馈类型",
        options=feedback_types_all,
        default=feedback_types_all
    )
    
    if view_mode == "💭 情感分析":
        st.markdown("---")
        st.subheader("情感筛选")
        sentiment_filter = st.multiselect(
            "选择情感类别",
            options=["正面", "中性", "负面"],
            default=["正面", "中性", "负面"]
        )
    
    st.info("💡 提示：使用上方筛选器来过滤数据")

if view_mode == "📊 反馈分析":
    st.title("📊 用户反馈分析面板")
    st.markdown("---")
    
    feedback_types, counts, dates, daily_feedback, satisfaction, satisfaction_counts = generate_mock_data()
    
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
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("🔔 反馈类型分布")
        
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
    
    st.markdown("---")
    st.subheader("😊 用户满意度分布")
    
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
    
    st.markdown("---")
    st.subheader("📋 反馈类型详细数据")
    
    df = pd.DataFrame({
        '反馈类型': feedback_types,
        '数量': counts,
        '占比': [f"{c/sum(counts)*100:.1f}%" for c in counts],
        '优先级': ['高', '中', '高', '紧急', '低', '低']
    })
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.title("💭 情感分析面板")
    st.markdown("---")
    
    feedback_df = generate_mock_feedback_data()
    
    if 'sentiment_filter' in locals():
        feedback_df = feedback_df[feedback_df['情感类别'].isin(sentiment_filter)]
    
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
            marker={
                'colors': sentiment_colors
            },
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
        st.subheader("📉 情感变化趋势")
        
        daily_sentiment = feedback_df.groupby([
            pd.Grouper(key='日期', freq='D'),
            '情感类别'
        ]).size().unstack(fill_value=0)
        
        for col in ['正面', '中性', '负面']:
            if col not in daily_sentiment.columns:
                daily_sentiment[col] = 0
        
        daily_sentiment = daily_sentiment[['正面', '中性', '负面']]
        
        fig_trend = go.Figure()
        
        color_map = {'正面': '#00CC96', '中性': '#FFA15A', '负面': '#EF553B'}
        
        for sentiment in daily_sentiment.columns:
            fig_trend.add_trace(go.Scatter(
                x=daily_sentiment.index,
                y=daily_sentiment[sentiment],
                mode='lines+markers',
                name=sentiment,
                line=dict(color=color_map[sentiment], width=3),
                marker=dict(size=7)
            ))
        
        fig_trend.update_layout(
            height=400,
            margin=dict(t=50, b=50, l=50, r=50),
            xaxis_title="日期",
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
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "反馈内容": st.column_config.TextColumn(
                "反馈内容",
                width="large"
            )
        }
    )
