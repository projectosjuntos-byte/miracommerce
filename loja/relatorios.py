import csv
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import Venda


def formatar_kz(valor):
    """Formata valor decimal no padrão angolano: 1.234.567,89 Kz"""
    if valor is None:
        valor = Decimal('0.00')
    val_float = float(valor)
    return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " Kz"


def formatar_numero(valor):
    """Formata número sem o sufixo Kz: 1.234.567,89"""
    if valor is None:
        valor = Decimal('0.00')
    val_float = float(valor)
    return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def filtrar_vendas(inicio=None, fim=None):
    """Retorna vendas filtradas por datas, com os relacionamentos necessários."""
    vendas = Venda.objects.select_related('produto', 'pedido', 'usuario').order_by('-data_venda', '-id')
    if inicio:
        inicio_dt = timezone.make_aware(datetime.combine(inicio, time.min))
        vendas = vendas.filter(data_venda__gte=inicio_dt)
    if fim:
        fim_dt = timezone.make_aware(datetime.combine(fim + timedelta(days=1), time.min))
        vendas = vendas.filter(data_venda__lt=fim_dt)
    return vendas


def total_venda(venda):
    """Retorna o preço unitário praticado na venda."""
    preco = venda.preco_unitario or (venda.produto.preco if venda.produto else Decimal('0.00'))
    return (preco or Decimal('0.00')).quantize(Decimal('0.01'))


def consolidar_vendas(vendas):
    """
    Agrupa registros da mesma transação e mesmo produto para consolidar itens
    adquiridos em conjunto, evitando linhas duplicadas de 1 unidade e calculando
    a quantidade real e o subtotal da linha.
    """
    itens_map = {}
    ordem = []

    for v in vendas:
        preco_unit = total_venda(v)
        produto_id = v.produto_id or 0
        chave = (v.id_transacao, produto_id, preco_unit)
        qtd = v.quantidade or 1

        if chave not in itens_map:
            usuario_display = 'Anônimo'
            if v.usuario:
                usuario_display = v.usuario.get_full_name() or v.usuario.username

            prod_nome = v.produto.nome if v.produto else f'Produto #{produto_id}'
            data_local = timezone.localtime(v.data_venda)

            itens_map[chave] = {
                'id_transacao': v.id_transacao,
                'data_venda': data_local,
                'data_texto': data_local.strftime('%d/%m/%Y %H:%M'),
                'produto_nome': prod_nome,
                'usuario_nome': usuario_display,
                'quantidade': qtd,
                'preco_unitario': preco_unit,
                'subtotal': (qtd * preco_unit).quantize(Decimal('0.01')),
            }
            ordem.append(chave)
        else:
            itens_map[chave]['quantidade'] += qtd
            itens_map[chave]['subtotal'] = (itens_map[chave]['quantidade'] * preco_unit).quantize(Decimal('0.01'))

    return [itens_map[k] for k in ordem]


def calcular_resumo_vendas(vendas):
    """Calcula indicadores chave (KPIs) a partir do conjunto de vendas filtrado."""
    itens = consolidar_vendas(vendas)
    total_receita = sum(item['subtotal'] for item in itens) if itens else Decimal('0.00')
    total_itens = sum(item['quantidade'] for item in itens) if itens else 0
    transacoes_set = {item['id_transacao'] for item in itens}
    total_transacoes = len(transacoes_set)
    ticket_medio = (total_receita / total_transacoes) if total_transacoes > 0 else Decimal('0.00')

    return {
        'total_receita': total_receita,
        'total_receita_formatado': formatar_kz(total_receita),
        'total_itens': total_itens,
        'total_transacoes': total_transacoes,
        'ticket_medio': ticket_medio,
        'ticket_medio_formatado': formatar_kz(ticket_medio),
        'itens_consolidados': itens,
    }


class NumberedCanvas(canvas.Canvas):
    """Canvas de dois passos para calcular o total real de páginas e renderizar rodapé/cabeçalho."""

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

        # Cabeçalho a partir da página 2
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor('#E2E8F0'))
            self.setLineWidth(0.5)
            self.line(15 * mm, 198 * mm, 282 * mm, 198 * mm)
            self.drawString(15 * mm, 201 * mm, 'MiraComerce IA — Relatório Consolidado de Vendas & Transações')
            self.drawRightString(282 * mm, 201 * mm, f'Página {self._pageNumber} de {page_count}')

        # Rodapé em todas as páginas
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.5)
        self.line(15 * mm, 12 * mm, 282 * mm, 12 * mm)
        self.drawString(15 * mm, 8 * mm, 'MiraComerce IA • Relatório Oficial de Auditoria e Gestão Comercial')
        self.drawRightString(282 * mm, 8 * mm, f'Página {self._pageNumber} de {page_count}')
        self.restoreState()


def _xml_escape(value):
    return (str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&apos;'))


def gerar_csv_relatorio_vendas(response, vendas):
    """Exporta CSV no padrão UTF-8 com BOM, incluindo quantidade e subtotal da linha."""
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';', lineterminator='\n')
    writer.writerow(['Transação', 'Data', 'Cliente', 'Produto', 'Quantidade', 'Preço unitário (Kz)', 'Subtotal (Kz)'])

    itens = consolidar_vendas(vendas)
    total_itens = 0
    total_receita = Decimal('0.00')

    for item in itens:
        total_itens += item['quantidade']
        total_receita += item['subtotal']
        writer.writerow([
            item['id_transacao'],
            item['data_texto'],
            item['usuario_nome'],
            item['produto_nome'],
            item['quantidade'],
            f"{item['preco_unitario']:.2f}",
            f"{item['subtotal']:.2f}",
        ])

    writer.writerow([])
    writer.writerow(['TOTAL GERAL', '', '', '', total_itens, '', f"{total_receita:.2f}"])
    return response


def gerar_excel_relatorio_vendas(response, vendas):
    """Gera SpreadsheetML XML nativo para Excel com cabeçalhos, quantidades e subtotais."""
    itens = consolidar_vendas(vendas)
    linhas = []
    total_itens = 0
    total_receita = Decimal('0.00')

    for item in itens:
        total_itens += item['quantidade']
        total_receita += item['subtotal']
        linhas.append(
            '<Row>'
            '<Cell><Data ss:Type="Number">{}</Data></Cell>'
            '<Cell><Data ss:Type="String">{}</Data></Cell>'
            '<Cell><Data ss:Type="String">{}</Data></Cell>'
            '<Cell><Data ss:Type="String">{}</Data></Cell>'
            '<Cell><Data ss:Type="Number">{}</Data></Cell>'
            '<Cell><Data ss:Type="Number">{:.2f}</Data></Cell>'
            '<Cell><Data ss:Type="Number">{:.2f}</Data></Cell>'
            '</Row>'.format(
                item['id_transacao'],
                _xml_escape(item['data_texto']),
                _xml_escape(item['usuario_nome']),
                _xml_escape(item['produto_nome']),
                item['quantidade'],
                item['preco_unitario'],
                item['subtotal'],
            )
        )

    # Linha de total no Excel
    linhas.append(
        '<Row>'
        '<Cell><Data ss:Type="String">TOTAL GERAL</Data></Cell>'
        '<Cell><Data ss:Type="String"></Data></Cell>'
        '<Cell><Data ss:Type="String"></Data></Cell>'
        '<Cell><Data ss:Type="String"></Data></Cell>'
        '<Cell><Data ss:Type="Number">{}</Data></Cell>'
        '<Cell><Data ss:Type="String"></Data></Cell>'
        '<Cell><Data ss:Type="Number">{:.2f}</Data></Cell>'
        '</Row>'.format(total_itens, total_receita)
    )

    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Vendas"><Table>
  <Row>
   <Cell><Data ss:Type="String">Transação</Data></Cell>
   <Cell><Data ss:Type="String">Data</Data></Cell>
   <Cell><Data ss:Type="String">Cliente</Data></Cell>
   <Cell><Data ss:Type="String">Produto</Data></Cell>
   <Cell><Data ss:Type="String">Quantidade</Data></Cell>
   <Cell><Data ss:Type="String">Preço unitário (Kz)</Data></Cell>
   <Cell><Data ss:Type="String">Subtotal (Kz)</Data></Cell>
  </Row>
  {}
 </Table></Worksheet></Workbook>'''.format(''.join(linhas))

    response.write(xml.encode('utf-8'))
    return response


def gerar_pdf_relatorio_vendas(response, vendas=None, inicio=None, fim=None, usuario=None):
    """
    Gera um relatório PDF executivo de alto padrão visual:
    - Identidade visual MiraComerce IA com logotipo e cabeçalho institucional.
    - Metadados de auditoria (data/hora de emissão, filtros aplicados, emissor).
    - Cartões de Resumo Executivo (KPIs: Receita, Transações, Artigos, Ticket Médio).
    - Tabela analítica consolidada com Subtotais por linha e Linha de Total Geral.
    - Paginação e rodapés dinâmicos através de NumberedCanvas.
    """
    vendas = vendas if vendas is not None else filtrar_vendas(inicio=inicio, fim=fim)
    resumo = calcular_resumo_vendas(vendas)
    itens = resumo['itens_consolidados']

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title='Relatório de Vendas — MiraComerce IA',
        author='MiraComerce IA',
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    style_prod = ParagraphStyle(
        'ProdName',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
    )
    style_cli = ParagraphStyle(
        'CliName',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155'),
    )

    story = []

    # 1. CABEÇALHO INSTITUCIONAL & METADADOS
    logo_path = Path(settings.BASE_DIR) / 'img' / 'logo-mira.png'
    logo_element = None
    if logo_path.exists():
        try:
            logo_element = RLImage(str(logo_path), width=28 * mm, height=18.6 * mm)
        except Exception:
            logo_element = None

    titulo_texto = (
        '<b><font size="15" color="#0F172A">MiraComerce IA</font></b><br/>'
        '<b><font size="10" color="#E67315">Relatório Analítico de Vendas &amp; Transações</font></b><br/>'
        '<font size="8" color="#64748B">Demonstrativo financeiro e operacional consolidado.</font>'
    )
    titulo_para = Paragraph(titulo_texto, styles['Normal'])

    if logo_element:
        header_left_content = [[logo_element, titulo_para]]
        t_left = Table(header_left_content, colWidths=[32 * mm, 143 * mm])
    else:
        header_left_content = [[titulo_para]]
        t_left = Table(header_left_content, colWidths=[175 * mm])

    t_left.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Bloco de auditoria (canto direito)
    agora_formatada = timezone.localtime(timezone.now()).strftime('%d/%m/%Y às %H:%M')
    if inicio and fim:
        periodo_str = f"{inicio.strftime('%d/%m/%Y')} até {fim.strftime('%d/%m/%Y')}"
    elif inicio:
        periodo_str = f"A partir de {inicio.strftime('%d/%m/%Y')}"
    elif fim:
        periodo_str = f"Até {fim.strftime('%d/%m/%Y')}"
    else:
        periodo_str = "Geral (Todo o Histórico)"

    emissor_nome = usuario.username if usuario else 'Administrador'

    meta_text = (
        '<font size="7.5" color="#475569">'
        f'<b>Emissão:</b> {agora_formatada}<br/>'
        f'<b>Período:</b> {periodo_str}<br/>'
        f'<b>Emitido por:</b> {emissor_nome}<br/>'
        '<b>Status:</b> Oficial &amp; Consolidado'
        '</font>'
    )
    meta_para = Paragraph(meta_text, styles['Normal'])

    header_table = Table([[t_left, meta_para]], colWidths=[175 * mm, 92 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#CBD5E1')),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (1, 0), (1, 0), 8),
        ('TOPPADDING', (1, 0), (1, 0), 6),
        ('BOTTOMPADDING', (1, 0), (1, 0), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # 2. CARTÕES DE RESUMO EXECUTIVO (KPIS)
    kpi_card_1 = Paragraph(
        f'<font size="7" color="#B45309"><b>FATURAMENTO TOTAL</b></font><br/>'
        f'<font size="12" color="#D97706"><b>{resumo["total_receita_formatado"]}</b></font><br/>'
        f'<font size="6.5" color="#92400E">Receita bruta consolidada</font>',
        styles['Normal'],
    )
    kpi_card_2 = Paragraph(
        f'<font size="7" color="#475569"><b>TRANSAÇÕES</b></font><br/>'
        f'<font size="12" color="#0F172A"><b>{resumo["total_transacoes"]} pedidos</b></font><br/>'
        f'<font size="6.5" color="#64748B">Transações no período</font>',
        styles['Normal'],
    )
    kpi_card_3 = Paragraph(
        f'<font size="7" color="#475569"><b>VOLUME VENDIDO</b></font><br/>'
        f'<font size="12" color="#0F172A"><b>{resumo["total_itens"]} artigos</b></font><br/>'
        f'<font size="6.5" color="#64748B">Unidades físicas expedidas</font>',
        styles['Normal'],
    )
    kpi_card_4 = Paragraph(
        f'<font size="7" color="#475569"><b>TICKET MÉDIO</b></font><br/>'
        f'<font size="12" color="#0F172A"><b>{resumo["ticket_medio_formatado"]}</b></font><br/>'
        f'<font size="6.5" color="#64748B">Média por transação</font>',
        styles['Normal'],
    )

    kpi_table = Table([[kpi_card_1, kpi_card_2, kpi_card_3, kpi_card_4]], colWidths=[66.75 * mm] * 4)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#FEF3C7')),
        ('BOX', (0, 0), (0, 0), 0.75, colors.HexColor('#F59E0B')),
        ('BACKGROUND', (1, 0), (-1, 0), colors.HexColor('#F8FAFC')),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#E2E8F0')),
        ('BOX', (2, 0), (2, 0), 0.5, colors.HexColor('#E2E8F0')),
        ('BOX', (3, 0), (3, 0), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 5 * mm))

    # 3. TABELA DETALHADA DE VENDAS
    # Largura total = 267 mm
    dados_tabela = [
        ['Transação', 'Data & Hora', 'Cliente', 'Produto', 'Qtd', 'Preço unitário (Kz)', 'Subtotal (Kz)']
    ]

    for item in itens:
        dados_tabela.append([
            str(item['id_transacao']),
            item['data_texto'],
            Paragraph(item['usuario_nome'], style_cli),
            Paragraph(item['produto_nome'], style_prod),
            str(item['quantidade']),
            formatar_numero(item['preco_unitario']),
            formatar_numero(item['subtotal']),
        ])

    if len(dados_tabela) == 1:
        dados_tabela.append(['—', '—', '—', Paragraph('Nenhuma venda registrada no período informado.', style_prod), '0', '0,00', '0,00'])

    # Linha de encerramento com Totais Gerais
    dados_tabela.append([
        'TOTAL GERAL CONSOLIDADO',
        '',
        '',
        '',
        str(resumo['total_itens']),
        '—',
        resumo['total_receita_formatado'],
    ])

    col_widths = [26 * mm, 34 * mm, 38 * mm, 79 * mm, 18 * mm, 36 * mm, 36 * mm]
    main_table = Table(dados_tabela, colWidths=col_widths, repeatRows=1)
    main_table.setStyle(TableStyle([
        # Cabeçalho da tabela
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A1D1E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#E67315')),
        # Alinhamentos
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (3, -1), 'LEFT'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Linhas de dados
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        # Linha de rodapé com Totais Gerais
        ('SPAN', (0, -1), (3, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEF3C7')),
        ('TEXTCOLOR', (0, -1), (3, -1), colors.HexColor('#0F172A')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 8.5),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#D97706')),
        ('ALIGN', (0, -1), (0, -1), 'LEFT'),
        ('ALIGN', (4, -1), (4, -1), 'CENTER'),
        ('ALIGN', (6, -1), (6, -1), 'RIGHT'),
        ('TEXTCOLOR', (6, -1), (6, -1), colors.HexColor('#B45309')),
    ]))

    story.append(main_table)
    doc.build(story, canvasmaker=NumberedCanvas)
    return response
