import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


CHINESE_FONT_PATHS = [
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/msyh.ttf',
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/arphic/ukai.ttc',
    '/System/Library/Fonts/PingFang.ttc',
]


def register_chinese_font():
    font_name = 'ChineseFont'
    for font_path in CHINESE_FONT_PATHS:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name
            except Exception:
                continue
    return 'Helvetica'


CHINESE_FONT = register_chinese_font()


PDF_PAGE_CONFIG = {
    'pagesize': A4,
    'rightMargin': 2 * cm,
    'leftMargin': 2 * cm,
    'topMargin': 2 * cm,
    'bottomMargin': 2 * cm,
}


def get_pdf_styles():
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName=CHINESE_FONT,
            fontSize=24,
            leading=30,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a5276')
        ),
        'subtitle': ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=11,
            leading=15,
            spaceAfter=10,
            alignment=TA_CENTER,
            textColor=colors.grey
        ),
        'section_title': ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName=CHINESE_FONT,
            fontSize=16,
            leading=22,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#2c3e50')
        ),
        'subsection_title': ParagraphStyle(
            'SubsectionTitle',
            parent=styles['Heading3'],
            fontName=CHINESE_FONT,
            fontSize=13,
            leading=18,
            spaceBefore=10,
            spaceAfter=8,
            textColor=colors.HexColor('#34495e')
        ),
        'normal': ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=10,
            leading=14,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ),
        'table_header': ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.white
        ),
        'table_cell': ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT
        ),
        'notes': ParagraphStyle(
            'Notes',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#7f8c8d')
        ),
        'footer': ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.grey
        ),
        'truncated': ParagraphStyle(
            'trunc',
            parent=styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.grey
        )
    }


def get_metric_table_style():
    return [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]


def get_data_table_style():
    return [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]


def get_excel_formats(workbook):
    return {
        'title': workbook.add_format({
            'bold': True,
            'font_size': 18,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': '微软雅黑',
            'font_color': '#1a5276'
        }),
        'subtitle': workbook.add_format({
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': '微软雅黑',
            'font_color': '#7f8c8d'
        }),
        'section': workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': '微软雅黑',
            'bg_color': '#d6eaf8',
            'font_color': '#2c3e50',
            'border': 1
        }),
        'header': workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': '微软雅黑',
            'bg_color': '#2c3e50',
            'font_color': 'white',
            'border': 1,
            'text_wrap': True
        }),
        'cell': workbook.add_format({
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': '微软雅黑',
            'border': 1,
            'text_wrap': True
        }),
        'alt_cell': workbook.add_format({
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': '微软雅黑',
            'border': 1,
            'bg_color': '#f8f9fa',
            'text_wrap': True
        }),
        'chart_title': workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_name': '微软雅黑',
            'font_color': '#34495e'
        })
    }


PDF_SECTION_TITLES = {
    'metrics': '一、关键指标摘要',
    'charts': '二、图表分析',
    'tables': '三、详细数据'
}


EXCEL_SHEET_NAMES = {
    'info': '报告信息',
    'metrics': '关键指标',
    'charts': '图表'
}


IMAGE_CONFIG = {
    'pdf': {
        'width': 15 * cm,
        'height': 9 * cm
    },
    'excel': {
        'x_scale': 0.8,
        'y_scale': 0.8,
        'row_offset': 35
    }
}


TABLE_CONFIG = {
    'max_display_rows': 50,
    'metric_col_widths': [5 * cm, 4 * cm, 7 * cm],
    'max_col_width': 4 * cm,
    'total_width': 16 * cm
}


REPORT_DEFAULT_TITLES = {
    "feedback": "用户反馈分析报告",
    "sentiment": "情感分析报告",
    "tickets": "工单统计报告"
}


AVAILABLE_CHARTS = {
    'feedback': {
        'type_distribution': '反馈类型分布饼图',
        'daily_trend': '每日反馈趋势折线图',
        'satisfaction': '用户满意度分布柱状图'
    },
    'sentiment': {
        'sentiment_pie': '情感占比分布饼图',
        'sentiment_trend': '情感变化趋势图',
        'sentiment_intensity_trend': '情感强度变化趋势图',
        'wordcloud': '反馈关键词词云'
    },
    'tickets': {
        'ticket_status': '工单状态分布',
        'ticket_priority': '工单优先级分布'
    }
}


AVAILABLE_DATA_TABLES = {
    'feedback': {
        'type_summary': '反馈类型摘要表',
        'feedback_detail': '详细反馈列表'
    },
    'sentiment': {
        'sentiment_summary': '情感分析摘要表',
        'sentiment_detail': '情感分析详细数据表',
        'keywords': '关键词统计表'
    },
    'tickets': {
        'ticket_summary': '工单统计摘要表',
        'ticket_detail': '工单详细列表'
    }
}


def get_available_items(page_type):
    charts = AVAILABLE_CHARTS.get(page_type, {})
    tables = AVAILABLE_DATA_TABLES.get(page_type, {})
    return charts, tables
