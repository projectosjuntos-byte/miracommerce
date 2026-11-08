import io
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
BASE_DIR = Path(__file__).resolve().parent.parent

logo_path = BASE_DIR / 'img' / 'logo-mira.png'
styles = getSampleStyleSheet()

class NumberedCanvas(canvas.Canvas):
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
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748B'))
        
        # Header on pages 2+
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor('#E2E8F0'))
            self.setLineWidth(0.5)
            self.line(15 * mm, 198 * mm, 282 * mm, 198 * mm)
            self.drawString(15 * mm, 201 * mm, 'MiraComerce IA — Relatório de Vendas e Transações')
            self.drawRightString(282 * mm, 201 * mm, f'Página {self._pageNumber} de {page_count}')

        # Footer on all pages
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.5)
        self.line(15 * mm, 12 * mm, 282 * mm, 12 * mm)
        self.drawString(15 * mm, 8 * mm, 'MiraComerce IA • Relatório Oficial de Auditoria e Gestão Comercial')
        self.drawRightString(282 * mm, 8 * mm, f'Página {self._pageNumber} de {page_count}')
        self.restoreState()

logo_img = RLImage(str(logo_path), width=28*mm, height=18.6*mm) if logo_path.exists() else ''

header_left = [
    [logo_img, Paragraph('<font size="15" color="#0F172A"><b>MiraComerce IA</b></font><br/><font size="10" color="#E67315"><b>Relatório Analítico de Vendas &amp; Transações</b></font><br/><font size="8" color="#64748B">Demonstrativo financeiro e operacional consolidado</font>', styles['Normal'])]
]
t_left = Table(header_left, colWidths=[32*mm, 140*mm])
t_left.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ('TOPPADDING', (0,0), (-1,-1), 0),
    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
]))

meta_text = (
    '<font size="7.5" color="#475569">'
    '<b>Emissão:</b> 01/11/2026 00:38<br/>'
    '<b>Período:</b> Todas as Vendas<br/>'
    '<b>Responsável:</b> admin1<br/>'
    '<b>Status:</b> Oficial &amp; Auditado'
    '</font>'
)
meta_para = Paragraph(meta_text, styles['Normal'])

header_table = Table([[t_left, meta_para]], colWidths=[175*mm, 92*mm])
header_table.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('BACKGROUND', (1,0), (1,0), colors.HexColor('#F8FAFC')),
    ('BOX', (1,0), (1,0), 0.5, colors.HexColor('#CBD5E1')),
    ('LEFTPADDING', (1,0), (1,0), 8),
    ('RIGHTPADDING', (1,0), (1,0), 8),
    ('TOPPADDING', (1,0), (1,0), 6),
    ('BOTTOMPADDING', (1,0), (1,0), 6),
]))

# KPI Cards
kpi_card_1 = Paragraph('<font size="7" color="#B45309"><b>FATURAMENTO TOTAL</b></font><br/><font size="12" color="#D97706"><b>113.040,00 Kz</b></font><br/><font size="6.5" color="#92400E">Receita bruta consolidada</font>', styles['Normal'])
kpi_card_2 = Paragraph('<font size="7" color="#475569"><b>TRANSAÇÕES</b></font><br/><font size="12" color="#0F172A"><b>5 pedidos</b></font><br/><font size="6.5" color="#64748B">Transações no período</font>', styles['Normal'])
kpi_card_3 = Paragraph('<font size="7" color="#475569"><b>VOLUME VENDIDO</b></font><br/><font size="12" color="#0F172A"><b>35 artigos</b></font><br/><font size="6.5" color="#64748B">Unidades físicas</font>', styles['Normal'])
kpi_card_4 = Paragraph('<font size="7" color="#475569"><b>TICKET MÉDIO</b></font><br/><font size="12" color="#0F172A"><b>22.608,00 Kz</b></font><br/><font size="6.5" color="#64748B">Média por pedido</font>', styles['Normal'])

kpi_table = Table([[kpi_card_1, kpi_card_2, kpi_card_3, kpi_card_4]], colWidths=[66.75*mm]*4)
kpi_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (0,0), colors.HexColor('#FEF3C7')),
    ('BOX', (0,0), (0,0), 0.75, colors.HexColor('#F59E0B')),
    ('BACKGROUND', (1,0), (-1,0), colors.HexColor('#F8FAFC')),
    ('BOX', (1,0), (1,0), 0.5, colors.HexColor('#E2E8F0')),
    ('BOX', (2,0), (2,0), 0.5, colors.HexColor('#E2E8F0')),
    ('BOX', (3,0), (3,0), 0.5, colors.HexColor('#E2E8F0')),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ('LEFTPADDING', (0,0), (-1,-1), 8),
    ('RIGHTPADDING', (0,0), (-1,-1), 8),
]))

# Sample table data
table_data = [
    ['Transação', 'Data & Hora', 'Cliente', 'Produto', 'Qtd', 'Preço Unit. (Kz)', 'Subtotal (Kz)'],
    ['2', '31/10/2026 22:04', 'Bedy', 'Arroz de Angola', '1', '3.200,00', '3.200,00'],
    ['2', '31/10/2026 22:04', 'Bedy', 'Feijão Carioca', '1', '2.320,00', '2.320,00'],
    ['1788303457', '01/09/2026 23:57', 'Justino', 'Carne de Vaca', '4', '5.200,00', '20.800,00'],
    ['1788303457', '01/09/2026 23:57', 'Justino', 'Óleo de Soja', '3', '2.600,00', '7.800,00'],
    ['1788303457', '01/09/2026 23:57', 'Justino', 'Feijão Carioca', '9', '2.900,00', '26.100,00'],
    ['TOTAL GERAL CONSOLIDADO', '', '', '', '18', '—', '60.220,00 Kz'],
]

main_table = Table(table_data, colWidths=[26*mm, 34*mm, 38*mm, 79*mm, 18*mm, 36*mm, 36*mm], repeatRows=1)
main_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A1D1E')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 8.5),
    ('ALIGN', (0,0), (1,-1), 'CENTER'),
    ('ALIGN', (2,0), (3,-1), 'LEFT'),
    ('ALIGN', (4,0), (4,-1), 'CENTER'),
    ('ALIGN', (5,0), (6,-1), 'RIGHT'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
    ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#E2E8F0')),
    ('TOPPADDING', (0,0), (-1,-1), 4.5),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
    ('LEFTPADDING', (0,0), (-1,-1), 5),
    ('RIGHTPADDING', (0,0), (-1,-1), 5),
    # Footer Row Styling
    ('SPAN', (0,-1), (3,-1)),
    ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
    ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor('#0F172A')),
    ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ('FONTSIZE', (0,-1), (-1,-1), 9),
    ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#D97706')),
    ('ALIGN', (0,-1), (0,-1), 'LEFT'),
    ('TEXTCOLOR', (6,-1), (6,-1), colors.HexColor('#B45309')),
]))

buf = io.BytesIO()
doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
story = [
    header_table,
    Spacer(1, 4*mm),
    kpi_table,
    Spacer(1, 5*mm),
    main_table
]
doc.build(story, canvasmaker=NumberedCanvas)
output_path = Path('scratch/output_test_relatorio.pdf')
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_bytes(buf.getvalue())
print('PDF written successfully to', output_path, 'Bytes:', len(buf.getvalue()))
