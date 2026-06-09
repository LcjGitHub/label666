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
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak, HRFlowable
)

import xlsxwriter

from report_templates import (
    CHINESE_FONT,
    PDF_PAGE_CONFIG,
    get_pdf_styles,
    get_metric_table_style,
    get_data_table_style,
    get_excel_formats,
    PDF_SECTION_TITLES,
    EXCEL_SHEET_NAMES,
    IMAGE_CONFIG,
    TABLE_CONFIG,
    AVAILABLE_CHARTS,
    AVAILABLE_DATA_TABLES,
    get_available_items
)


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
        pagesize=PDF_PAGE_CONFIG['pagesize'],
        rightMargin=PDF_PAGE_CONFIG['rightMargin'],
        leftMargin=PDF_PAGE_CONFIG['leftMargin'],
        topMargin=PDF_PAGE_CONFIG['topMargin'],
        bottomMargin=PDF_PAGE_CONFIG['bottomMargin'],
        title=report_title
    )
    
    styles = get_pdf_styles()
    elements = []
    
    elements.append(Paragraph(report_title, styles['title']))
    elements.append(Paragraph(f"报告生成日期：{report_date}", styles['subtitle']))
    
    if report_notes:
        elements.append(Spacer(1, 5 * mm))
        elements.append(HRFlowable(width="80%", thickness=1, color=colors.grey, spaceAfter=5))
        elements.append(Paragraph(f"<b>备注：</b>{report_notes}", styles['notes']))
    
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2c3e50')))
    elements.append(Spacer(1, 5 * mm))
    
    elements.append(Paragraph(PDF_SECTION_TITLES['metrics'], styles['section_title']))
    
    if key_metrics:
        metric_data = [['指标名称', '数值', '说明']]
        for metric in key_metrics:
            metric_data.append([
                Paragraph(str(metric.get('label', '')), styles['table_cell']),
                Paragraph(str(metric.get('value', '')), styles['table_cell']),
                Paragraph(str(metric.get('delta', '')), styles['table_cell'])
            ])
        
        metric_table = Table(metric_data, colWidths=TABLE_CONFIG['metric_col_widths'])
        metric_table.setStyle(TableStyle(get_metric_table_style()))
        elements.append(metric_table)
    else:
        elements.append(Paragraph("暂无关键指标数据", styles['normal']))
    
    elements.append(Spacer(1, 5 * mm))
    elements.append(PageBreak())
    
    chart_config = AVAILABLE_CHARTS.get(page_type, {})
    if selected_charts and chart_images:
        elements.append(Paragraph(PDF_SECTION_TITLES['charts'], styles['section_title']))
        
        chart_idx = 1
        for chart_id in selected_charts:
            if chart_id in chart_images:
                chart_title = chart_config.get(chart_id, chart_id)
                elements.append(Paragraph(f"{chart_idx}. {chart_title}", styles['subsection_title']))
                
                img_data = chart_images[chart_id]
                if isinstance(img_data, Image.Image):
                    img_data = save_pil_image_to_bytes(img_data)
                
                if img_data:
                    try:
                        img = RLImage(
                            img_data,
                            width=IMAGE_CONFIG['pdf']['width'],
                            height=IMAGE_CONFIG['pdf']['height']
                        )
                        img.hAlign = 'CENTER'
                        elements.append(img)
                    except Exception:
                        elements.append(Paragraph("[图表渲染失败]", styles['normal']))
                
                elements.append(Spacer(1, 5 * mm))
                chart_idx += 1
        
        elements.append(PageBreak())
    
    table_config = AVAILABLE_DATA_TABLES.get(page_type, {})
    if selected_tables and data_frames:
        elements.append(Paragraph(PDF_SECTION_TITLES['tables'], styles['section_title']))
        
        table_idx = 1
        for table_id in selected_tables:
            if table_id in data_frames:
                table_title = table_config.get(table_id, table_id)
                df = data_frames[table_id]
                
                if df is not None and not df.empty:
                    elements.append(Paragraph(f"{table_idx}. {table_title}", styles['subsection_title']))
                    
                    max_rows = TABLE_CONFIG['max_display_rows']
                    display_df = df.head(max_rows).copy()
                    
                    table_data = []
                    headers = [Paragraph(str(col), styles['table_header']) for col in display_df.columns]
                    table_data.append(headers)
                    
                    for _, row in display_df.iterrows():
                        table_data.append([
                            Paragraph(str(val)[:100] if pd.notna(val) else '', styles['table_cell'])
                            for val in row.values
                        ])
                    
                    if len(df) > max_rows:
                        table_data.append([
                            Paragraph(
                                f"... 共 {len(df)} 条数据，仅显示前 {max_rows} 条",
                                styles['truncated']
                            )
                            for _ in display_df.columns
                        ])
                    
                    num_cols = len(display_df.columns)
                    if num_cols > 0:
                        col_width = min(
                            TABLE_CONFIG['total_width'] / num_cols,
                            TABLE_CONFIG['max_col_width']
                        )
                        col_widths = [col_width] * num_cols
                    else:
                        col_widths = [4 * cm]
                    
                    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                    
                    style_cmds = get_data_table_style().copy()
                    
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
    elements.append(Paragraph(
        f"本报告由用户反馈分析系统自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['footer']
    ))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def _get_or_create_worksheet(workbook, sheet_name):
    existing_sheets = [ws.get_name() for ws in workbook.worksheets()]
    if sheet_name in existing_sheets:
        idx = existing_sheets.index(sheet_name)
        return workbook.worksheets()[idx]
    return workbook.add_worksheet(sheet_name)


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
    
    fmt = get_excel_formats(workbook)
    
    info_ws = _get_or_create_worksheet(workbook, EXCEL_SHEET_NAMES['info'])
    info_ws.set_column('A:A', 20)
    info_ws.set_column('B:B', 60)
    
    info_ws.merge_range('A1:B1', report_title, fmt['title'])
    info_ws.set_row(0, 40)
    
    info_ws.write('A3', '报告生成日期', fmt['subtitle'])
    info_ws.write('B3', report_date, fmt['subtitle'])
    
    if report_notes:
        info_ws.write('A4', '备注信息', fmt['subtitle'])
        info_ws.write('B4', report_notes, fmt['subtitle'])
    
    info_ws.write('A6', '生成时间', fmt['subtitle'])
    info_ws.write('B6', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), fmt['subtitle'])
    
    if key_metrics:
        metrics_ws = _get_or_create_worksheet(workbook, EXCEL_SHEET_NAMES['metrics'])
        metrics_ws.set_column('A:C', 30)
        
        row = 0
        metrics_ws.merge_range(f'A{row+1}:C{row+1}', PDF_SECTION_TITLES['metrics'], fmt['section'])
        metrics_ws.set_row(row, 25)
        row += 1
        
        headers = ['指标名称', '数值', '说明']
        for col, header in enumerate(headers):
            metrics_ws.write(row, col, header, fmt['header'])
        metrics_ws.set_row(row, 20)
        row += 1
        
        for metric in key_metrics:
            cell_fmt = fmt['cell'] if row % 2 == 0 else fmt['alt_cell']
            metrics_ws.write(row, 0, str(metric.get('label', '')), cell_fmt)
            metrics_ws.write(row, 1, str(metric.get('value', '')), cell_fmt)
            metrics_ws.write(row, 2, str(metric.get('delta', '')), cell_fmt)
            row += 1
    
    chart_config = AVAILABLE_CHARTS.get(page_type, {})
    if selected_charts and chart_images:
        chart_ws = _get_or_create_worksheet(workbook, EXCEL_SHEET_NAMES['charts'])
        chart_ws.set_column('A:A', 100)
        
        row = 0
        chart_ws.merge_range(f'A{row+1}:Z{row+1}', PDF_SECTION_TITLES['charts'], fmt['section'])
        chart_ws.set_row(row, 25)
        row += 2
        
        for chart_id in selected_charts:
            if chart_id in chart_images:
                chart_title = chart_config.get(chart_id, chart_id)
                chart_ws.write(row, 0, chart_title, fmt['chart_title'])
                row += 1
                
                img_data = chart_images[chart_id]
                if isinstance(img_data, Image.Image):
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        img_data.save(tmp, format='PNG')
                        tmp_path = tmp.name
                    
                    try:
                        chart_ws.insert_image(row, 0, tmp_path, {
                            'x_scale': IMAGE_CONFIG['excel']['x_scale'],
                            'y_scale': IMAGE_CONFIG['excel']['y_scale']
                        })
                        row += IMAGE_CONFIG['excel']['row_offset']
                    finally:
                        os.unlink(tmp_path)
                elif isinstance(img_data, io.BytesIO):
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp.write(img_data.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        chart_ws.insert_image(row, 0, tmp_path, {
                            'x_scale': IMAGE_CONFIG['excel']['x_scale'],
                            'y_scale': IMAGE_CONFIG['excel']['y_scale']
                        })
                        row += IMAGE_CONFIG['excel']['row_offset']
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
                    
                    ws = _get_or_create_worksheet(workbook, safe_sheet_name)
                    
                    row = 0
                    ws.merge_range(
                        0, 0, 0, max(len(df.columns) - 1, 0),
                        table_config.get(table_id, table_id),
                        fmt['section']
                    )
                    ws.set_row(row, 25)
                    row += 1
                    
                    for col, col_name in enumerate(df.columns):
                        ws.write(row, col, str(col_name), fmt['header'])
                        max_len = max(len(str(col_name)), 10)
                        for val in df[col_name].astype(str).values[:100]:
                            max_len = max(max_len, min(len(val), 50))
                        ws.set_column(col, col, min(max_len + 2, 50))
                    
                    ws.set_row(row, 20)
                    row += 1
                    
                    for _, data_row in df.iterrows():
                        cell_fmt = fmt['cell'] if row % 2 == 0 else fmt['alt_cell']
                        for col, val in enumerate(data_row.values):
                            if pd.isna(val):
                                ws.write(row, col, '', cell_fmt)
                            else:
                                ws.write(row, col, str(val), cell_fmt)
                        row += 1
    
    workbook.close()
    buffer.seek(0)
    return buffer
