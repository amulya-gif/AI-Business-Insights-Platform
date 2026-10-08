import io
import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from src.kpis import truncate_label, format_metric_val

class NumberedCanvas(canvas.Canvas):
    """Custom canvas to generate dynamic headers, footers, and page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Suppress headers/footers on the cover page
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#1a365d"))
            self.drawString(54, 755, "AI EXECUTIVE DECISION INTELLIGENCE PLATFORM")
            
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#718096"))
            self.drawRightString(558, 755, "EXECUTIVE BRIEFING")
            
            # Header Rule
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(54, 747, 558, 747)
            
            # Footer
            self.line(54, 52, 558, 52)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#718096"))
            self.drawString(54, 40, "CONFIDENTIAL - STRATEGIC DECISION SUPPORT")
            
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(558, 40, page_text)
            
        else:
            # Draw decorative sidebar background on cover page
            self.setFillColor(colors.HexColor("#1a365d"))
            self.rect(0, 0, 18, 792, fill=True, stroke=False)
            
            self.setFillColor(colors.HexColor("#319795"))  # Accent teal bar
            self.rect(18, 0, 8, 792, fill=True, stroke=False)
            
        self.restoreState()

def parse_markdown_to_flowables(markdown_text, styles):
    """Helper to convert Markdown text into ReportLab Flowable objects with HTML styling."""
    import re
    flowables = []
    lines = markdown_text.split('\n')
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                flowables.append(Spacer(1, 4))
            continue
            
        # Parse titles
        if line.startswith('## '):
            in_list = False
            title = line[3:]
            title = re.sub(r'[^\x00-\x7F]+', '', title).strip()
            flowables.append(Spacer(1, 14))
            flowables.append(Paragraph(title, styles['ExecHeading']))
            flowables.append(Spacer(1, 6))
        elif line.startswith('# '):
            in_list = False
            title = line[2:]
            title = re.sub(r'[^\x00-\x7F]+', '', title).strip()
            flowables.append(Spacer(1, 18))
            flowables.append(Paragraph(title, styles['ExecHeadingMajor']))
            flowables.append(Spacer(1, 8))
        # Parse bullet points
        elif line.startswith('- ') or line.startswith('* ') or (len(line) > 2 and line[0].isdigit() and line[1:].startswith('. ')):
            in_list = True
            content = line[2:] if line.startswith('- ') or line.startswith('* ') else line[3:]
            content = re.sub(r'[^\x00-\x7F]+', '', content).strip()
            
            while '**' in content:
                content = content.replace('**', '<b>', 1).replace('**', '</b>', 1)
            flowables.append(Paragraph(content, styles['ExecBullet']))
        # Standard paragraph text
        else:
            in_list = False
            content = line
            content = re.sub(r'[^\x00-\x7F]+', '', content).strip()
            while '**' in content:
                content = content.replace('**', '<b>', 1).replace('**', '</b>', 1)
            flowables.append(Paragraph(content, styles['ExecBody']))
            flowables.append(Spacer(1, 8))
            
    return flowables

def generate_pdf_report(kpis, df_clean, date_col, region_col, product_col, revenue_col, profit_col, report_markdown, industry):
    """Compiles dashboard analytics and the Strategic Report into a consulting-grade PDF document. Gracefully handles missing profit data."""
    buffer = io.BytesIO()
    if df_clean is None or df_clean.empty:
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=72,
            bottomMargin=72
        )
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='WarningTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor("#1a365d"),
            spaceAfter=20
        ))
        styles.add(ParagraphStyle(
            name='WarningBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor("#2d3748")
        ))
        story = [
            Spacer(1, 40),
            Paragraph("Strategic Briefing PDF Exporter", styles['WarningTitle']),
            Paragraph("This report is unavailable because the uploaded CSV dataset is empty or invalid.", styles['WarningBody'])
        ]
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()
        
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom executive styles
    styles.add(ParagraphStyle(
        name='CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=30
    ))
    styles.add(ParagraphStyle(
        name='CoverMetadataLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2d3748")
    ))
    styles.add(ParagraphStyle(
        name='CoverMetadataVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4a5568")
    ))
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2d3748")
    ))
    styles.add(ParagraphStyle(
        name='TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1a365d")
    ))
    styles.add(ParagraphStyle(
        name='TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2d3748"),
        alignment=2
    ))
    styles.add(ParagraphStyle(
        name='ExecHeadingMajor',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1a365d"),
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name='ExecHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2b6cb0"),
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name='ExecBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2d3748")
    ))
    styles.add(ParagraphStyle(
        name='ExecBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2d3748"),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    ))
    
    story = []
    
    # ---------------------------------------------------------
    # COVER PAGE
    # ---------------------------------------------------------
    story.append(Spacer(1, 40))
    story.append(Paragraph("<b>⯈ ACCENTURE STRATEGY & CONSULTING</b>", ParagraphStyle(
        'AccentureHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#a0aec0"), spaceAfter=60
    )))
    
    story.append(Paragraph("AI Executive Decision Intelligence Platform", styles['CoverTitle']))
    story.append(Paragraph("AI-powered executive analytics for business strategy, performance monitoring and decision support.", styles['CoverSubtitle']))
    
    story.append(Spacer(1, 40))
    
    has_profit = profit_col and profit_col in df_clean.columns

    # Metadata Box
    metadata_data = [
        [Paragraph("INDUSTRY SECTOR:", styles['CoverMetadataLabel']), Paragraph(industry, styles['CoverMetadataVal'])],
        [Paragraph("BUSINESS HEALTH SCORE:", styles['CoverMetadataLabel']), Paragraph(f"<b>{kpis['health_score']}/100</b> ({kpis['health_status']})", styles['CoverMetadataVal'])],
        [Paragraph("TOTAL REVENUE:", styles['CoverMetadataLabel']), Paragraph(f"${kpis['total_revenue']:,.2f}", styles['CoverMetadataVal'])],
        [Paragraph("TOTAL NET PROFIT:", styles['CoverMetadataLabel']), Paragraph(f"${kpis['total_profit']:,.2f} ({kpis['profit_margin']:.1f}% Margin)" if has_profit else "N/A (Profit details missing)", styles['CoverMetadataVal'])],
        [Paragraph("REPORT DATE:", styles['CoverMetadataLabel']), Paragraph(datetime.datetime.now().strftime("%B %d, %Y"), styles['CoverMetadataVal'])]
    ]
    
    metadata_table = Table(metadata_data, colWidths=[160, 340])
    metadata_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(metadata_table)
    story.append(PageBreak())
    
    # ---------------------------------------------------------
    # PAGE 2: FINANCIAL SUMMARY & OPERATIONAL TABLES
    # ---------------------------------------------------------
    story.append(Paragraph("Financial Summary & Operational Performance", styles['ExecHeadingMajor']))
    story.append(Spacer(1, 10))
    
    # Table 1: Regional Sales breakdown
    story.append(Paragraph("Geographic Performance Breakdown", styles['ExecHeading']))
    story.append(Spacer(1, 4))
    
    # Group and calculate region metrics
    region_group = [revenue_col]
    if has_profit:
        region_group.append(profit_col)
        
    region_perf = df_clean.groupby(region_col)[region_group].sum()
    region_perf['share'] = (region_perf[revenue_col] / kpis['total_revenue'] * 100)
    region_perf = region_perf.sort_values(by=revenue_col, ascending=False).head(15) # Show top 15 regions to avoid giant list
    
    if has_profit:
        region_perf['margin'] = (region_perf[profit_col] / region_perf[revenue_col] * 100)
        region_table_data = [[
            Paragraph("Region", styles['TableHeader']),
            Paragraph("Revenue ($)", styles['TableHeader']),
            Paragraph("Revenue Share (%)", styles['TableHeader']),
            Paragraph("Net Profit ($)", styles['TableHeader']),
            Paragraph("Profit Margin (%)", styles['TableHeader'])
        ]]
        for idx, row in region_perf.iterrows():
            region_table_data.append([
                Paragraph(truncate_label(str(idx), 20), styles['TableCellBold']),
                Paragraph(f"{row[revenue_col]:,.2f}", styles['TableCellRight']),
                Paragraph(f"{row['share']:.1f}%", styles['TableCellRight']),
                Paragraph(f"{row[profit_col]:,.2f}", styles['TableCellRight']),
                Paragraph(f"{row['margin']:.1f}%", styles['TableCellRight'])
            ])
        col_widths = [100, 100, 100, 100, 100]
    else:
        region_table_data = [[
            Paragraph("Region", styles['TableHeader']),
            Paragraph("Revenue ($)", styles['TableHeader']),
            Paragraph("Revenue Share (%)", styles['TableHeader'])
        ]]
        for idx, row in region_perf.iterrows():
            region_table_data.append([
                Paragraph(truncate_label(str(idx), 25), styles['TableCellBold']),
                Paragraph(f"{row[revenue_col]:,.2f}", styles['TableCellRight']),
                Paragraph(f"{row['share']:.1f}%", styles['TableCellRight'])
            ])
        col_widths = [180, 160, 160]
        
    region_table = Table(region_table_data, colWidths=col_widths)
    region_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a365d")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(region_table)
    
    story.append(Spacer(1, 20))
    
    # Table 2: Product Performance breakdown (Top 15 categories)
    story.append(Paragraph("Product Segment Analysis", styles['ExecHeading']))
    story.append(Spacer(1, 4))
    
    product_group = [revenue_col]
    if has_profit:
        product_group.append(profit_col)
        
    product_perf = df_clean.groupby(product_col)[product_group].sum()
    
    if has_profit:
        product_perf = product_perf.sort_values(by=profit_col, ascending=False).head(15)
        product_perf['margin'] = (product_perf[profit_col] / product_perf[revenue_col] * 100)
        
        product_table_data = [[
            Paragraph("Product Category", styles['TableHeader']),
            Paragraph("Revenue ($)", styles['TableHeader']),
            Paragraph("Net Profit ($)", styles['TableHeader']),
            Paragraph("Profit Margin (%)", styles['TableHeader'])
        ]]
        for idx, row in product_perf.iterrows():
            product_table_data.append([
                Paragraph(truncate_label(str(idx), 20), styles['TableCellBold']),
                Paragraph(f"{row[revenue_col]:,.2f}", styles['TableCellRight']),
                Paragraph(f"{row[profit_col]:,.2f}", styles['TableCellRight']),
                Paragraph(f"{row['margin']:.1f}%", styles['TableCellRight'])
            ])
        p_col_widths = [170, 110, 110, 110]
    else:
        product_perf = product_perf.sort_values(by=revenue_col, ascending=False).head(15)
        product_table_data = [[
            Paragraph("Product Category", styles['TableHeader']),
            Paragraph("Revenue ($)", styles['TableHeader']),
            Paragraph("Revenue Share (%)", styles['TableHeader'])
        ]]
        for idx, row in product_perf.iterrows():
            product_table_data.append([
                Paragraph(truncate_label(str(idx), 25), styles['TableCellBold']),
                Paragraph(f"{row[revenue_col]:,.2f}", styles['TableCellRight']),
                Paragraph(f"{(row[revenue_col]/kpis['total_revenue']*100):.1f}%", styles['TableCellRight'])
            ])
        p_col_widths = [180, 160, 160]
        
    product_table = Table(product_table_data, colWidths=p_col_widths)
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2b6cb0")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(product_table)
    
    story.append(PageBreak())
    
    # ---------------------------------------------------------
    # PAGE 3+: STRATEGIC DECISION BRIEFING
    # ---------------------------------------------------------
    story.append(Paragraph("Strategic Decision Briefing", styles['ExecHeadingMajor']))
    story.append(Spacer(1, 10))
    
    brief_flowables = parse_markdown_to_flowables(report_markdown, styles)
    story.extend(brief_flowables)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    
    buffer.seek(0)
    return buffer.getvalue()
