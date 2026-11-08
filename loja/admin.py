from django.contrib import admin
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
from .auditoria import registrar_auditoria, snapshot_modelo
from .estoque import registrar_movimentacao_apos_ajuste
from .models import (
    AuditoriaAdministrativa,
    Categoria,
    HistoricoStatusPedido,
    ItemPedido,
    MovimentacaoEstoque,
    Pagamento,
    Pedido,
    Perfil,
    Produto,
    SubCategoria,
    Venda,
)

# ==============================================================================
# CONFIGURAÇÕES GERAIS DO PAINEL (MIRACOMERCE IA)
# ==============================================================================
admin.site.site_header = 'MiraComerce IA - Gestão Estratégica'
admin.site.index_title = 'Painel de Controlo de Stock e Inteligência'
admin.site.site_title = 'MiraComerce IA'


class AuditedModelAdmin(admin.ModelAdmin):
    """Registra criações e alterações feitas pelo painel administrativo."""

    def save_model(self, request, obj, form, change):
        anterior = None
        if change and obj.pk:
            anterior = snapshot_modelo(self.model.objects.get(pk=obj.pk))

        super().save_model(request, obj, form, change)
        atual = snapshot_modelo(obj)
        alteracoes = (
            {'after': atual}
            if anterior is None
            else {
                campo: {'before': anterior.get(campo), 'after': valor}
                for campo, valor in atual.items()
                if anterior.get(campo) != valor
            }
        )
        if alteracoes:
            registrar_auditoria(
                request,
                acao='update' if anterior is not None else 'create',
                objeto=obj,
                alteracoes=alteracoes,
            )

    def delete_model(self, request, obj):
        snapshot = snapshot_modelo(obj)
        super().delete_model(request, obj)
        registrar_auditoria(request, acao='delete', objeto=obj, alteracoes={'before': snapshot})

# ==============================================================================
# 1. CATEGORIAS
# ==============================================================================
@admin.register(Categoria)
class CategoriaAdmin(AuditedModelAdmin):
    list_display = ('id', 'nome', 'slug')
    prepopulated_fields = {'slug': ('nome',)}
    search_fields = ('nome',)
    ordering = ('id',)

@admin.register(SubCategoria)
class SubCategoriaAdmin(AuditedModelAdmin):
    list_display = ('id', 'categoria', 'nome', 'slug')
    prepopulated_fields = {'slug': ('nome',)}
    search_fields = ('nome', 'categoria__nome')
    ordering = ('categoria__nome', 'nome')
    fieldsets = (
        ('Categoria e subcategoria', {
            'fields': ('categoria', 'nome', 'slug')
        }),
    )

# ==============================================================================
# 2. PRODUTOS (COM ALERTAS VISUAIS DE STOCK IA E FORMATAÇÃO DE MOEDA)
# ==============================================================================
@admin.register(Produto)
class ProdutoAdmin(AuditedModelAdmin):
    list_display = ('sku', 'nome', 'categoria', 'subcategoria', 'exibir_preco', 'quantidade_estoque', 'status_stock_ia', 'em_promocao')
    list_filter = ('categoria', 'subcategoria', 'em_promocao', 'status_promocao')
    search_fields = ('sku', 'nome', 'categoria__nome', 'subcategoria__nome')
    list_editable = ('quantidade_estoque', 'em_promocao')
    fieldsets = (
        ('Dados do produto', {
            'fields': ('sku', 'nome', 'categoria', 'subcategoria', 'imagem')
        }),
        ('Preço e estoque', {
            'fields': ('preco', 'preco_promocional', 'em_promocao', 'quantidade_estoque', 'data_validade')
        }),
    )
    readonly_fields = ('sku',)

    def save_model(self, request, obj, form, change):
        saldo_anterior = 0
        if change and obj.pk:
            saldo_anterior = self.model.objects.get(pk=obj.pk).quantidade_estoque
        super().save_model(request, obj, form, change)
        tipo = MovimentacaoEstoque.Tipo.ENTRADA if obj.quantidade_estoque >= saldo_anterior else MovimentacaoEstoque.Tipo.AJUSTE
        registrar_movimentacao_apos_ajuste(
            obj,
            saldo_anterior,
            tipo,
            usuario=request.user,
            referencia=f'Admin Produto #{obj.pk}',
            observacao='Alteração de estoque realizada no painel administrativo.',
        )
    
    def exibir_preco(self, obj):
        # intcomma transforma 1200.00 em 1.200,00 (ou 1,200.00 dependendo do seu LANGUAGE_CODE)
        valor_com_pontos = intcomma(f"{obj.preco:,.2f}")
        # Substituímos vírgulas por pontos se quiser o padrão exato de Angola (1.200,00)
        # Se o seu Django já estiver em PT-PT ou PT-BR, o intcomma pode fazer isso sozinho.
        return format_html('<b>{} Kz</b>', valor_com_pontos)
    
    exibir_preco.short_description = 'Preço Unitário'

    def status_stock_ia(self, obj):
        if obj.quantidade_estoque <= 0:
            return format_html('<span style="color: #e74c3c; font-weight: bold;">🔴 ESGOTADO</span>')
        elif obj.quantidade_estoque < 5:
            return format_html('<span style="color: #f39c12; font-weight: bold;">⚠️ REPOR (Crítico)</span>')
        return format_html('<span style="color: #27ae60;">✅ Normal</span>')
    
    status_stock_ia.short_description = 'Status IA'

# ==============================================================================
# 3. PERFIL DO UTILIZADOR (ANGOLA)
# ==============================================================================
@admin.register(Perfil)
class PerfilAdmin(AuditedModelAdmin):
    list_display = ('usuario', 'telefone', 'provincia', 'municipio', 'exibir_bonus')
    search_fields = ('usuario__username', 'telefone')
    list_filter = ('provincia',)

    def exibir_bonus(self, obj):
        valor_com_pontos = intcomma(f"{obj.saldo_bonus:,.2f}")
        return format_html('<span>{} Kz</span>', valor_com_pontos)
    
    exibir_bonus.short_description = 'Saldo Bónus'

# ==============================================================================
# 4. VENDAS (HISTÓRICO PARA ALGORITMO APRIORI)
# ==============================================================================
@admin.register(Venda)
class VendaAdmin(AuditedModelAdmin):
    list_display = ('id_transacao', 'usuario', 'produto', 'quantidade', 'data_venda')
    list_filter = ('data_venda', 'produto__categoria')
    search_fields = ('id_transacao', 'usuario__username', 'produto__nome')
    readonly_fields = (
        'id_transacao',
        'data_venda',
        'produto',
        'usuario',
        'pedido',
        'preco_unitario',
        'quantidade',
    )

    def has_delete_permission(self, request, obj=None):
        return False

# ==============================================================================
# 5. PEDIDOS E ITENS (PROCESSO DE CHECKOUT)
# ==============================================================================
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ('produto', 'quantidade', 'preco_unitario', 'subtotal')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Pedido)
class PedidoAdmin(AuditedModelAdmin):
    list_display = ('id', 'usuario', 'data_criacao', 'exibir_status', 'total', 'exibir_finalizado')
    list_filter = ('status', 'finalizado', 'data_criacao')
    search_fields = ('id', 'usuario__username', 'usuario__email')
    inlines = [ItemPedidoInline]
    readonly_fields = ('usuario', 'data_criacao', 'finalizado', 'total', 'idempotency_key')
    actions = ['marcar_como_preparacao', 'marcar_como_transporte', 'marcar_como_entregue']

    def save_model(self, request, obj, form, change):
        obj._status_actor_id = request.user.pk
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def exibir_status(self, obj):
        badge = obj.badge_status
        return format_html(
            '<span class="badge {}" style="padding: 5px 10px; font-size: 0.82rem;">{}</span>',
            badge.get('classe', 'bg-secondary'),
            badge.get('label', obj.get_status_display()),
        )
    exibir_status.short_description = 'Status'

    def exibir_finalizado(self, obj):
        if obj.finalizado:
            return format_html('<span style="color: #27ae60; font-weight: bold;">✔ Sim</span>')
        return format_html('<span style="color: #f39c12;">⏳ Pendente</span>')
    exibir_finalizado.short_description = 'Finalizado?'

    @admin.action(description='Marcar pedidos selecionados como Em Preparação')
    def marcar_como_preparacao(self, request, queryset):
        for pedido in queryset:
            pedido._status_actor_id = request.user.pk
            pedido.status = Pedido.Status.PROCESSING
            pedido.save()
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como Em Preparação.')

    @admin.action(description='Marcar pedidos selecionados como Em Transporte')
    def marcar_como_transporte(self, request, queryset):
        for pedido in queryset:
            pedido._status_actor_id = request.user.pk
            pedido.status = Pedido.Status.SHIPPED
            pedido.save()
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como Em Transporte.')

    @admin.action(description='Marcar pedidos selecionados como Entregue')
    def marcar_como_entregue(self, request, queryset):
        for pedido in queryset:
            pedido._status_actor_id = request.user.pk
            pedido.status = Pedido.Status.DELIVERED
            pedido.save()
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como Entregue.')


@admin.register(Pagamento)
class PagamentoAdmin(AuditedModelAdmin):
    list_display = ('pedido', 'status', 'provider', 'valor', 'criado_em')
    list_filter = ('status', 'provider', 'criado_em')
    search_fields = ('pedido__id', 'provider_transaction_id')
    readonly_fields = (
        'pedido',
        'status',
        'provider',
        'provider_transaction_id',
        'idempotency_key',
        'valor',
        'criado_em',
        'atualizado_em',
        'detalhes',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'produto', 'tipo', 'quantidade', 'saldo_anterior', 'saldo_posterior', 'usuario', 'pedido')
    list_filter = ('tipo', 'criado_em')
    search_fields = ('produto__sku', 'produto__nome', 'referencia')
    readonly_fields = tuple(field.name for field in MovimentacaoEstoque._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoricoStatusPedido)
class HistoricoStatusPedidoAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'pedido', 'status_anterior', 'status_novo', 'usuario')
    list_filter = ('status_novo', 'criado_em')
    search_fields = ('pedido__id', 'pedido__usuario__username')
    readonly_fields = tuple(field.name for field in HistoricoStatusPedido._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditoriaAdministrativa)
class AuditoriaAdministrativaAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'usuario', 'acao', 'modelo', 'objeto_id', 'ip_address')
    list_filter = ('acao', 'modelo', 'criado_em')
    search_fields = ('modelo', 'objeto_id', 'usuario__username', 'ip_address')
    readonly_fields = tuple(field.name for field in AuditoriaAdministrativa._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
