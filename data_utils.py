import numpy as np
import pandas as pd
import jieba
import uuid
from wordcloud import WordCloud
from collections import Counter

POSITIVE_WORDS = [
    "太棒了", "非常好", "非常满意", "真的棒", "真的好", "很满意", "很喜欢",
    "很不错", "太好了", "太好了", "超级棒", "超级好", "优秀", "满意", "喜欢",
    "赞", "不错", "很好", "完美", "出色", "厉害", "方便", "快速", "高效",
    "流畅", "稳定", "实用", "清晰", "简洁", "美观", "贴心", "智能",
    "人性化", "惊喜", "感谢", "支持", "推荐", "值得", "舒服", "顺畅",
    "省心", "靠谱", "专业", "及时", "热情", "友好", "细致", "耐心",
    "点赞", "好用", "强大", "满意", "提高了", "提升", "改善"
]

NEGATIVE_WORDS = [
    "太差", "太差了", "很难用", "太卡", "太慢", "太差劲", "太糟糕",
    "很失望", "很讨厌", "崩溃", "报错", "失败", "难用", "复杂", "混乱",
    "麻烦", "垃圾", "恶心", "无语", "坑爹", "离谱", "气人", "烦人",
    "浪费", "骗", "虚假", "推卸", "敷衍", "拖沓", "低效", "卡顿",
    "闪退", "黑屏", "出错", "bug", "故障", "难看", "反人类", "迟钝",
    "太贵", "不满意", "不好用", "不好", "不行", "糟糕", "讨厌",
    "失望", "差", "烂", "慢", "卡", "气"
]

NEUTRAL_PHRASES = [
    "还可以", "中规中矩", "一般般", "一般吧", "还行", "过得去",
    "马马虎虎", "普普通通", "平平", "凑合", "一般般吧", "一般来说",
    "整体还行", "整体一般", "没什么", "没太大"
]

NEGATION_WORDS = ["不", "没", "没有", "不太", "不够", "不是", "难以"]

def analyze_sentiment(text):
    text = str(text)
    
    for phrase in NEUTRAL_PHRASES:
        if phrase in text:
            return "中性", 0
    
    pos_count = 0
    neg_count = 0
    
    for word in POSITIVE_WORDS:
        if word in text:
            idx = text.find(word)
            context = text[max(0, idx - 6):idx]
            has_negation = any(nw in context for nw in NEGATION_WORDS)
            if has_negation:
                neg_count += 1
            else:
                pos_count += 1
    
    for word in NEGATIVE_WORDS:
        if word in text:
            idx = text.find(word)
            context = text[max(0, idx - 6):idx]
            has_negation = any(nw in context for nw in NEGATION_WORDS)
            if has_negation:
                pos_count += 1
            else:
                neg_count += 1
    
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
    
    feedback_types_pool = [
        "功能建议", "界面优化", "性能问题", "Bug 报告", "使用咨询", "其他"
    ]
    
    dates = pd.date_range(start="2024-01-01", periods=len(feedback_texts), freq="18H")
    sentiments = []
    scores = []
    types = []
    
    np.random.seed(42)
    for text in feedback_texts:
        sentiment, score = analyze_sentiment(text)
        sentiments.append(sentiment)
        scores.append(score)
        types.append(np.random.choice(feedback_types_pool))
    
    feedback_ids = [f"FB-{uuid.uuid4().hex[:8].upper()}" for _ in feedback_texts]
    
    df = pd.DataFrame({
        '反馈ID': feedback_ids,
        '日期': dates,
        '反馈内容': feedback_texts,
        '反馈类型': types,
        '情感类别': sentiments,
        '情感强度': scores
    })
    
    return df

def generate_feedback_summary_data():
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
    
    daily_df = pd.DataFrame({
        '日期': dates,
        '反馈数量': daily_feedback
    })
    
    return feedback_types, counts, daily_df, satisfaction, satisfaction_counts

def filter_by_date(df, date_column, start_date, end_date):
    if isinstance(start_date, list) and len(start_date) == 2:
        start_date, end_date = start_date[0], start_date[1]
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    return df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]

def filter_by_feedback_type(df, type_column, selected_types):
    if not selected_types:
        return df
    return df[df[type_column].isin(selected_types)]

def filter_by_sentiment(df, sentiment_column, selected_sentiments):
    if not selected_sentiments:
        return df
    return df[df[sentiment_column].isin(selected_sentiments)]

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
