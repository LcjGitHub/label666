import os
import io
import tempfile
from datetime import datetime
import pandas as pd
import numpy as np
from PIL import Image
import plotly.graph_objects as go

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

import xlsxwriter


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


AVAILABLE_CHARTS = {
    'feedback': {
        'type_distribution': '反馈类型分布饼图',
        'daily_trend': '每日反馈趋势折线图',
        'satisfaction': '用户满意度分布柱状图'
    },
    'sentiment': {
        'sentiment_pie': '情感占比分布饼图',
        'sentiment_trend': '情感变化趋势图',
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


def convert_figure_to_image(fig, width=800, height=500, scale=2):
    try:
        img_bytes = fig.to_image(
            format='png',
            width=width,
            height=height,
            scale=scale
        )
        return io.BytesIO(img_bytes)
    except Exception:
        return None


def save_pil_image_to_bytes(pil_img, format='PNG'):
    img_buffer = io.BytesIO()
    pil_img.save(img_buffer, format=format)
    img_buffer.seek(0)
    return img_buffer


def create_pdf_report(
    report_title,
    report_date,
    report_notes,
    page_type,
    selected_charts,
    selected_tables,
    chart_images,
    data_frames,
    key_metrics
):
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=report_title
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=CHINESE_FONT,
        fontSize=24,
        leading=30,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a5276')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName=CHINESE_FONT,
        fontSize=11,
        leading=15,
        spaceAfter=10,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName=CHINESE_FONT,
        fontSize=16,
        leading=22,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#2c3e50')
    )
    
    subsection_title_style = ParagraphStyle(
        'SubsectionTitle',
        parent=styles['Heading3'],
        fontName=CHINESE_FONT,
        fontSize=13,
        leading=18,
        spaceBefore=10,
        spaceAfter=8,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=CHINESE_FONT,
        fontSize=10,
        leading=14,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName=CHINESE_FONT,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName=CHINESE_FONT,
        fontSize=9,
        leading=12,
        alignment=TA_LEFT
    )
    
    elements = []
    
    elements.append(Paragraph(report_title, title_style))
    elements.append(Paragraph(f"报告生成日期：{report_date}", subtitle_style))
    
    if report_notes:
        elements.append(Spacer(1, 5 * mm))
        elements.append(HRFlowable(width="80%", thickness=1, color=colors.grey, spaceAfter=5))
        elements.append(Paragraph(f"<b>备注：</b>{report_notes}", ParagraphStyle(
            'Notes',
            parent=normal_style,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#7f8c8d')
        )))
    
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2c3e50')))
    elements.append(Spacer(1, 5 * mm))
    
    elements.append(Paragraph("一、关键指标摘要", section_title_style))
    
    if key_metrics:
        metric_data = [['指标名称', '数值', '说明']]
        for metric in key_metrics:
            metric_data.append([
                Paragraph(str(metric.get('label', '')), table_cell_style),
                Paragraph(str(metric.get('value', '')), table_cell_style),
                Paragraph(str(metric.get('delta', '')), table_cell_style)
            ])
        
        metric_table = Table(metric_data, colWidths=[5 * cm, 4 * cm, 7 * cm])
        metric_table.setStyle(TableStyle([
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
        ]))
        elements.append(metric_table)
    else:
        elements.append(Paragraph("暂无关键指标数据", normal_style))
    
    elements.append(Spacer(1, 5 * mm))
    elements.append(PageBreak())
    
    chart_config = AVAILABLE_CHARTS.get(page_type, {})
    if selected_charts and chart_images:
        elements.append(Paragraph("二、图表分析", section_title_style))
        
        chart_idx = 1
        for chart_id in selected_charts:
            if chart_id in chart_images:
                chart_title = chart_config.get(chart_id, chart_id)
                elements.append(Paragraph(f"{chart_idx}. {chart_title}", subsection_title_style))
                
                img_data = chart_images[chart_id]
                if isinstance(img_data, Image.Image):
                    img_data = save_pil_image_to_bytes(img_data)
                
                if img_data:
                    try:
                        img = RLImage(img_data, width=15 * cm, height=9 * cm)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                    except Exception:
                        elements.append(Paragraph("[图表渲染失败]", normal_style))
                
                elements.append(Spacer(1, 5 * mm))
                chart_idx += 1
        
        elements.append(PageBreak())
    
    table_config = AVAILABLE_DATA_TABLES.get(page_type, {})
    if selected_tables and data_frames:
        elements.append(Paragraph("三、详细数据", section_title_style))
        
        table_idx = 1
        for table_id in selected_tables:
            if table_id in data_frames:
                table_title = table_config.get(table_id, table_id)
                df = data_frames[table_id]
                
                if df is not None and not df.empty:
                    elements.append(Paragraph(f"{table_idx}. {table_title}", subsection_title_style))
                    
                    max_rows = 50
                    display_df = df.head(max_rows).copy()
                    
                    table_data = []
                    headers = [Paragraph(str(col), table_header_style) for col in display_df.columns]
                    table_data.append(headers)
                    
                    for _, row in display_df.iterrows():
                        table_data.append([
                            Paragraph(str(val)[:100] if pd.notna(val) else '', table_cell_style)
                            for val in row.values
                        ])
                    
                    if len(df) > max_rows:
                        table_data.append([
                            Paragraph(f"... 共 {len(df)} 条数据，仅显示前 {max_rows} 条", 
                                     ParagraphStyle('trunc', parent=table_cell_style, textColor=colors.grey))
                            for _ in display_df.columns
                        ])
                    
                    num_cols = len(display_df.columns)
                    if num_cols > 0:
                        col_width = min(16 * cm / num_cols, 4 * cm)
                        col_widths = [col_width] * num_cols
                    else:
                        col_widths = [4 * cm]
                    
                    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                    
                    style_cmds = [
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
                    
                    if len(df) > max_rows:
                        style_cmds.append(('SPAN', (0, -1), (-1, -1)))
                        style_cmds.append(('ALIGN', (0, -1), (-1, -1), 'CENTER'))
                    
                    data_table.setStyle(TableStyle(style_cmds))
                    elements.append(data_table)
                    elements.append(Spacer(1, 5 * mm))
                    table_idx += 1
        
        elements.append(Spacer(1, 1 * cm))
    
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 3 * mm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=CHINESE_FONT,
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph(
        f"本报告由用户反馈分析系统自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        footer_style
    ))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def create_excel_report(
    report_title,
    report_date,
    report_notes,
    page_type,
    selected_charts,
    selected_tables,
    chart_images,
    data_frames,
    key_metrics
):
    buffer = io.BytesIO()
    
    workbook = xlsxwriter.Workbook(buffer, {
        'in_memory': True,
        'default_date_format': 'yyyy-mm-dd'
    })
    
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 18,
        'align': 'center',
        'valign': 'vcenter',
        'font_name': '微软雅黑',
        'font_color': '#1a5276'
    })
    
    subtitle_format = workbook.add_format({
        'font_size': 11,
        'align': 'center',
        'valign': 'vcenter',
        'font_name': '微软雅黑',
        'font_color': '#7f8c8d'
    })
    
    section_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'left',
        'valign': 'vcenter',
        'font_name': '微软雅黑',
        'bg_color': '#d6eaf8',
        'font_color': '#2c3e50',
        'border': 1
    })
    
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 11,
        'align': 'center',
        'valign': 'vcenter',
        'font_name': '微软雅黑',
        'bg_color': '#2c3e50',
        'font_color': 'white',
        'border': 1,
        'text_wrap': True
    })
    
    cell_format = workbook.add_format({
        'font_size': 10,
        'align': 'left',
        'valign': 'vcenter',
        'font_name': '微软雅黑',
        'border': 1,
        'text_wrap': True
    })
    
    alt_cell_format = workbook.add_format({
        'font_size': 10,
        'align': 'left',
        'valign': 'vcenter',
        'font_name': '微软雅黑',
        'border': 1,
        'bg_color': '#f8f9fa',
        'text_wrap': True
    })
    
    info_worksheet = workbook.add_worksheet('报告信息')
    info_worksheet.set_column('A:A', 20)
    info_worksheet.set_column('B:B', 60)
    
    info_worksheet.merge_range('A1:B1', report_title, title_format)
    info_worksheet.set_row(0, 40)
    
    info_worksheet.write('A3', '报告生成日期', subtitle_format)
    info_worksheet.write('B3', report_date, subtitle_format)
    
    if report_notes:
        info_worksheet.write('A4', '备注信息', subtitle_format)
        info_worksheet.write('B4', report_notes, subtitle_format)
    
    info_worksheet.write('A6', '生成时间', subtitle_format)
    info_worksheet.write('B6', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), subtitle_format)
    
    if key_metrics:
        metrics_worksheet = workbook.add_worksheet('关键指标')
        metrics_worksheet.set_column('A:C', 30)
        
        row = 0
        metrics_worksheet.merge_range(f'A{row+1}:C{row+1}', '一、关键指标摘要', section_format)
        metrics_worksheet.set_row(row, 25)
        row += 1
        
        headers = ['指标名称', '数值', '说明']
        for col, header in enumerate(headers):
            metrics_worksheet.write(row, col, header, header_format)
        metrics_worksheet.set_row(row, 20)
        row += 1
        
        for metric in key_metrics:
            fmt = cell_format if row % 2 == 0 else alt_cell_format
            metrics_worksheet.write(row, 0, str(metric.get('label', '')), fmt)
            metrics_worksheet.write(row, 1, str(metric.get('value', '')), fmt)
            metrics_worksheet.write(row, 2, str(metric.get('delta', '')), fmt)
            row += 1
    
    chart_config = AVAILABLE_CHARTS.get(page_type, {})
    if selected_charts and chart_images:
        chart_worksheet = workbook.add_worksheet('图表')
        chart_worksheet.set_column('A:A', 100)
        
        row = 0
        chart_worksheet.merge_range(f'A{row+1}:Z{row+1}', '二、图表分析', section_format)
        chart_worksheet.set_row(row, 25)
        row += 2
        
        for chart_id in selected_charts:
            if chart_id in chart_images:
                chart_title = chart_config.get(chart_id, chart_id)
                chart_worksheet.write(row, 0, chart_title, workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'font_name': '微软雅黑',
                    'font_color': '#34495e'
                }))
                row += 1
                
                img_data = chart_images[chart_id]
                if isinstance(img_data, Image.Image):
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        img_data.save(tmp, format='PNG')
                        tmp_path = tmp.name
                    
                    try:
                        chart_worksheet.insert_image(row, 0, tmp_path, {
                            'x_scale': 0.8,
                            'y_scale': 0.8
                        })
                        row += 35
                    finally:
                        os.unlink(tmp_path)
                elif isinstance(img_data, io.BytesIO):
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp.write(img_data.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        chart_worksheet.insert_image(row, 0, tmp_path, {
                            'x_scale': 0.8,
                            'y_scale': 0.8
                        })
                        row += 35
                    finally:
                        os.unlink(tmp_path)
                else:
                    row += 2
    
    table_config = AVAILABLE_DATA_TABLES.get(page_type, {})
    if selected_tables and data_frames:
        for table_id in selected_tables:
            if table_id in data_frames:
                df = data_frames[table_id]
                if df is not None and not df.empty:
                    sheet_name = table_config.get(table_id, table_id)[:31]
                    safe_sheet_name = ''.join(c for c in sheet_name if c not in '[]:*?/\\')
                    if not safe_sheet_name:
                        safe_sheet_name = f'Table_{table_id}'
                    
                    try:
                        ws = workbook.get_worksheet_by_name(safe_sheet_name)
                    except Exception:
                        ws = workbook.add_worksheet(safe_sheet_name)
                    
                    row = 0
                    ws.merge_range(
                        0, 0, 0, max(len(df.columns) - 1, 0),
                        table_config.get(table_id, table_id),
                        section_format
                    )
                    ws.set_row(row, 25)
                    row += 1
                    
                    for col, col_name in enumerate(df.columns):
                        ws.write(row, col, str(col_name), header_format)
                        max_len = max(len(str(col_name)), 10)
                        for val in df[col_name].astype(str).values[:100]:
                            max_len = max(max_len, min(len(val), 50))
                        ws.set_column(col, col, min(max_len + 2, 50))
                    
                    ws.set_row(row, 20)
                    row += 1
                    
                    for _, data_row in df.iterrows():
                        fmt = cell_format if row % 2 == 0 else alt_cell_format
                        for col, val in enumerate(data_row.values):
                            if pd.isna(val):
                                ws.write(row, col, '', fmt)
                            else:
                                ws.write(row, col, str(val), fmt)
                        row += 1
    
    workbook.close()
    buffer.seek(0)
    return buffer
