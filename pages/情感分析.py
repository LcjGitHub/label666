import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
from auth_utils import (
    init_session,
    is_logged_in,
    render_login_page,
    render_user_info_in_sidebar,
    has_permission
)
from data_utils import (
    generate_mock_feedback_data,
    filter_by_date,
    filter_by_feedback_type,
    filter_by_sentiment,
    extract_keywords,
    create_wordcloud
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
from report_utils import (
    create_pdf_report,
    create_excel_report,
    convert_figure_to_image,
    save_pil_image_to_bytes,
    get_available_items
)

st.set_page_config(
    page_title="情感分析",
    page_icon="💭",
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

feedback_df = generate_mock_feedback_data()

with st.sidebar:
    render_user_info_in_sidebar()
    display_config = load_display_config()
    if display_config.get("show_sidebar_notification", True):
        render_sidebar_notification_center()
    filters = render_sidebar(current_page="sentiment")

if filters.get("date_range") and len(filters["date_range"]) == 2:
    feedback_df = filter_by_date(feedback_df, "日期", filters["date_range"][0], filters["date_range"][1])

if filters.get("feedback_type"):
    feedback_df = filter_by_feedback_type(feedback_df, "反馈类型", filters["feedback_type"])

if filters.get("sentiment_type"):
    feedback_df = filter_by_sentiment(feedback_df, "情感类别", filters["sentiment_type"])

st.title("💭 情感分析面板")

if has_permission("edit_config") or has_permission("export_data"):
    report_config = render_report_export_section("sentiment")
else:
    report_config = {
        "title": "情感分析报告",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "notes": "",
        "charts": [],
        "tables": []
    }

if "show_report_preview_sentiment" not in st.session_state:
    st.session_state.show_report_preview_sentiment = False

if has_permission("export_data"):
    col_preview, col_export_pdf, col_export_excel = st.columns([1, 1, 1])
    with col_preview:
        if st.button("👁️ 报告预览", use_container_width=True, type="secondary"):
            st.session_state.show_report_preview_sentiment = not st.session_state.show_report_preview_sentiment
else:
    st.info("💡 提示：如需导出报告功能，请联系管理员开通「导出数据」权限。")

st.markdown("---")

total_count = len(feedback_df)
pos_count = len(feedback_df[feedback_df['情感类别'] == '正面'])
neu_count = len(feedback_df[feedback_df['情感类别'] == '中性'])
neg_count = len(feedback_df[feedback_df['情感类别'] == '负面'])

pos_pct = f"{pos_count/total_count*100:.1f}%" if total_count > 0 else "0%"
neu_pct = f"{neu_count/total_count*100:.1f}%" if total_count > 0 else "0%"
neg_pct = f"{neg_count/total_count*100:.1f}%" if total_count > 0 else "0%"

key_metrics = [
    {"label": "总反馈数", "value": total_count, "delta": "样本总数"},
    {"label": "正面反馈", "value": f"{pos_count}", "delta": pos_pct},
    {"label": "中性反馈", "value": f"{neu_count}", "delta": neu_pct},
    {"label": "负面反馈", "value": f"{neg_count}", "delta": neg_pct}
]

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

    plotly_config = {
        'displayModeBar': can_export,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['sendDataToCloud', 'lasso2d', 'select2d']
    }
    
    st.plotly_chart(fig_pie, use_container_width=True, config=plotly_config)

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
    
    st.plotly_chart(fig_trend, use_container_width=True, config=plotly_config)

st.markdown("---")

st.subheader("📈 情感强度变化趋势（日平均）")

daily_intensity = feedback_df.groupby(
    pd.Grouper(key='日期', freq='D')
).agg(
    平均情感强度=('情感强度', 'mean'),
    反馈数量=('情感强度', 'count')
).reset_index()

daily_intensity['日期'] = daily_intensity['日期'].dt.strftime('%Y-%m-%d')
daily_intensity['平均情感强度'] = daily_intensity['平均情感强度'].round(2)

fig_intensity = go.Figure()

fig_intensity.add_trace(go.Scatter(
    x=daily_intensity['日期'],
    y=daily_intensity['平均情感强度'],
    mode='lines+markers',
    name='平均情感强度',
    line=dict(color='#636EFA', width=3),
    marker=dict(size=10),
    hovertemplate='日期: %{x}<br>平均情感强度: %{y}<br>反馈数量: %{customdata}<extra></extra>',
    customdata=daily_intensity['反馈数量']
))

fig_intensity.add_trace(go.Scatter(
    x=daily_intensity['日期'],
    y=[0] * len(daily_intensity),
    mode='lines',
    name='中性基准线',
    line=dict(color='#95A5A6', width=1, dash='dash'),
    showlegend=True
))

fig_intensity.update_layout(
    height=420,
    margin=dict(t=50, b=50, l=50, r=50),
    xaxis_title="日期",
    yaxis_title="平均情感强度",
    hovermode='x unified',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.2,
        xanchor="center",
        x=0.5
    ),
    yaxis=dict(
        zeroline=True,
        zerolinecolor='#95A5A6',
        zerolinewidth=1
    )
)

st.plotly_chart(fig_intensity, use_container_width=True, config=plotly_config)

intensity_col1, intensity_col2, intensity_col3 = st.columns(3)
avg_intensity_all = feedback_df['情感强度'].mean()
max_intensity_day = daily_intensity.loc[daily_intensity['平均情感强度'].idxmax()] if len(daily_intensity) > 0 else None
min_intensity_day = daily_intensity.loc[daily_intensity['平均情感强度'].idxmin()] if len(daily_intensity) > 0 else None

with intensity_col1:
    st.metric(
        label="整体平均情感强度",
        value=f"{avg_intensity_all:.2f}" if not pd.isna(avg_intensity_all) else "N/A"
    )
with intensity_col2:
    if max_intensity_day is not None:
        st.metric(
            label="最高情感强度日",
            value=f"{max_intensity_day['平均情感强度']:.2f}",
            delta=max_intensity_day['日期']
        )
    else:
        st.metric(label="最高情感强度日", value="N/A")
with intensity_col3:
    if min_intensity_day is not None:
        st.metric(
            label="最低情感强度日",
            value=f"{min_intensity_day['平均情感强度']:.2f}",
            delta=min_intensity_day['日期'],
            delta_color="inverse"
        )
    else:
        st.metric(label="最低情感强度日", value="N/A")

avg_intensity_str = f"{avg_intensity_all:.2f}" if not pd.isna(avg_intensity_all) else "N/A"
max_intensity_str = f"{max_intensity_day['平均情感强度']:.2f}" if max_intensity_day is not None else "N/A"
min_intensity_str = f"{min_intensity_day['平均情感强度']:.2f}" if min_intensity_day is not None else "N/A"
max_intensity_date = max_intensity_day['日期'] if max_intensity_day is not None else ""
min_intensity_date = min_intensity_day['日期'] if min_intensity_day is not None else ""

key_metrics.extend([
    {"label": "整体平均情感强度", "value": avg_intensity_str, "delta": "所有反馈均值"},
    {"label": "最高情感强度日", "value": max_intensity_str, "delta": max_intensity_date},
    {"label": "最低情感强度日", "value": min_intensity_str, "delta": min_intensity_date}
])

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
        
        if can_export:
            st.dataframe(
                words_df,
                use_container_width=True,
                height=400
            )
        else:
            st.table(words_df)
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

sentiment_display_df = display_df.copy()
if can_export:
    st.dataframe(
        sentiment_display_df[['日期', '反馈类型', '情感类别', '情感强度', '反馈内容']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "反馈内容": st.column_config.TextColumn(
                "反馈内容",
                width="large"
            )
        }
    )
else:
    st.dataframe(
        sentiment_display_df[['日期', '反馈类型', '情感类别', '情感强度', '反馈内容']],
        use_container_width=True,
        hide_index=True
    )

chart_images = {}
if report_config["charts"]:
    if "sentiment_pie" in report_config["charts"]:
        chart_images["sentiment_pie"] = convert_figure_to_image(fig_pie)
    if "sentiment_trend" in report_config["charts"]:
        chart_images["sentiment_trend"] = convert_figure_to_image(fig_trend)
    if "sentiment_intensity_trend" in report_config["charts"]:
        chart_images["sentiment_intensity_trend"] = convert_figure_to_image(fig_intensity)
    if "wordcloud" in report_config["charts"] and word_freq and wc_img:
        chart_images["wordcloud"] = wc_img

df_sentiment_summary = pd.DataFrame({
    '情感类别': ['正面', '中性', '负面'],
    '数量': [pos_count, neu_count, neg_count],
    '占比': [pos_pct, neu_pct, neg_pct]
})

df_intensity_daily = daily_intensity.copy()
df_intensity_daily.columns = ['日期', '平均情感强度', '反馈数量']

data_frames = {}
if report_config["tables"]:
    if "sentiment_summary" in report_config["tables"]:
        data_frames["sentiment_summary"] = df_sentiment_summary
    if "sentiment_detail" in report_config["tables"]:
        detail_export = feedback_df.copy()
        detail_export['日期'] = detail_export['日期'].dt.strftime('%Y-%m-%d')
        data_frames["sentiment_detail"] = detail_export[['反馈ID', '日期', '反馈类型', '情感类别', '情感强度', '反馈内容']]
    if "sentiment_intensity_daily" in report_config["tables"]:
        data_frames["sentiment_intensity_daily"] = df_intensity_daily
    if "keywords" in report_config["tables"] and word_freq:
        data_frames["keywords"] = pd.DataFrame(word_freq, columns=['关键词', '出现次数'])

sentiment_pdf_buffer = None
sentiment_excel_buffer = None
if report_config["charts"] or report_config["tables"]:
    sentiment_pdf_buffer = create_pdf_report(
        report_title=report_config["title"],
        report_date=report_config["date"],
        report_notes=report_config["notes"],
        page_type="sentiment",
        selected_charts=report_config["charts"],
        selected_tables=report_config["tables"],
        chart_images=chart_images,
        data_frames=data_frames,
        key_metrics=key_metrics
    )
    sentiment_excel_buffer = create_excel_report(
        report_title=report_config["title"],
        report_date=report_config["date"],
        report_notes=report_config["notes"],
        page_type="sentiment",
        selected_charts=report_config["charts"],
        selected_tables=report_config["tables"],
        chart_images=chart_images,
        data_frames=data_frames,
        key_metrics=key_metrics
    )

if has_permission("export_data") and st.session_state.show_report_preview_sentiment:
    st.markdown("---")
    st.subheader("📄 报告预览")
    
    with st.container():
        col_pdf, col_excel = st.columns(2)
        with col_pdf:
            if sentiment_pdf_buffer:
                st.download_button(
                    label="📥 导出 PDF",
                    data=sentiment_pdf_buffer,
                    file_name=f"{report_config['title']}_{report_config['date']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="sentiment_pdf_download"
                )
            else:
                st.info("请至少选择一个图表或数据表格")
        
        with col_excel:
            if sentiment_excel_buffer:
                st.download_button(
                    label="📊 导出 Excel",
                    data=sentiment_excel_buffer,
                    file_name=f"{report_config['title']}_{report_config['date']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                    key="sentiment_excel_download"
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
        
        chart_names, table_names = get_available_items("sentiment")
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
