from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from datetime import date, timedelta

from .validators import validate_product_image
from .image_utils import thumbnail_upload_path


def produto_upload_path(instance, filename):
    """Store images with opaque names, never using user-controlled paths."""
    suffix = Path(filename or '').suffix.lower()
    if suffix not in {'.jpg', '.jpeg', '.png', '.webp'}:
        suffix = '.bin'
    return f'produtos/{uuid4().hex}{suffix}'

# 1. CATEGORIAS (Para organizar a vitrine e subcategorias)
class Categoria(models.Model):
    nome = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, null=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

class SubCategoria(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias', db_index=True)
    nome = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, null=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.categoria.nome} / {self.nome}"

# 2. PRODUTOS (Com lógica de validade e promoção)
class Produto(models.Model):
    sku = models.CharField(max_length=32, unique=True, db_index=True, editable=False)
    nome = models.CharField(max_length=100, db_index=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    subcategoria = models.ForeignKey(SubCategoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos', db_index=True)
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    quantidade_estoque = models.PositiveIntegerField(default=0, db_index=True)
    data_validade = models.DateField(null=True, blank=True, db_index=True)
    status_promocao = models.BooleanField(default=False, db_index=True)
    imagem = models.ImageField(
        upload_to=produto_upload_path,
        validators=[validate_product_image],
        blank=True,
        null=True,
    )
    thumbnail = models.ImageField(
        upload_to=thumbnail_upload_path,
        blank=True,
        null=True,
        editable=False,
    )
    preco_promocional = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    em_promocao = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f'MRC-{uuid4().hex[:12].upper()}'
        super().save(*args, **kwargs)

    def clean(self):
        if self.subcategoria_id and self.categoria_id:
            if self.subcategoria.categoria_id != self.categoria_id:
                raise ValidationError({'subcategoria': 'A subcategoria deve pertencer à categoria selecionada.'})

        if self.preco_promocional is not None and self.preco_promocional > self.preco:
            raise ValidationError({'preco_promocional': 'O preço promocional não pode ser maior que o preço normal.'})

    @property
    def esta_expirado(self):
        return bool(self.data_validade and self.data_validade < date.today())

    def aplicar_promocao_automatica(self, dias_para_expirar=90):
        hoje = date.today()
        limite_validade = hoje + timedelta(days=dias_para_expirar)

        if self.esta_expirado:
            self.em_promocao = False
            self.status_promocao = False
            self.preco_promocional = None
            return self

        # Promoção marcada manualmente no admin: mantém ativa mesmo sem validade.
        if self.em_promocao:
            if self.preco_promocional is None:
                self.preco_promocional = (self.preco * Decimal('0.80')).quantize(Decimal('0.01'))
            self.status_promocao = True
            return self

        # Regra automática por validade.
        if self.data_validade and hoje <= self.data_validade <= limite_validade:
            self.em_promocao = True
            self.status_promocao = True
            self.preco_promocional = (self.preco * Decimal('0.80')).quantize(Decimal('0.01'))
        else:
            self.em_promocao = False
            self.status_promocao = False
            self.preco_promocional = None

        return self

    def obter_preco_venda(self, dias_para_expirar=90):
        hoje = date.today()
        limite_validade = hoje + timedelta(days=dias_para_expirar)

        if self.esta_expirado:
            return self.preco

        if self.em_promocao:
            if self.preco_promocional is not None:
                return self.preco_promocional
            return (self.preco * Decimal('0.80')).quantize(Decimal('0.01'))

        if self.data_validade and hoje <= self.data_validade <= limite_validade:
            if self.preco_promocional is not None:
                return self.preco_promocional
            return (self.preco * Decimal('0.80')).quantize(Decimal('0.01'))
        return self.preco

    def __str__(self):
        return self.nome

# 3. PERFIL DO UTILIZADOR (Dados extras e Saldo de Bónus)
class Perfil(models.Model):
    IDIOMA_CHOICES = (
        ('pt-pt', 'Português'),
        ('en', 'English'),
    )
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, db_index=True)
    idioma = models.CharField(max_length=5, choices=IDIOMA_CHOICES, default='pt-pt')
    telefone = models.CharField(max_length=20, blank=True, null=True)
    provincia = models.CharField(max_length=50, blank=True, null=True)
    municipio = models.CharField(max_length=50, blank=True, null=True)
    bairro = models.CharField(max_length=50, blank=True, null=True)
    saldo_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_compras_realizadas = models.PositiveIntegerField(default=0, db_index=True)

    def adicionar_bonus(self, valor):
        self.saldo_bonus = (self.saldo_bonus or Decimal('0.00')) + Decimal(str(valor))
        return self.saldo_bonus

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

# 4. VENDAS (Tabela histórica que alimenta a IA de sugestões)
class Venda(models.Model):
    # id_transacao agrupa itens comprados juntos para análise de regras de associação
    id_transacao = models.BigIntegerField(db_index=True)
    data_venda = models.DateTimeField(auto_now_add=True, db_index=True)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, db_index=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, db_index=True)
    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='vendas',
        db_index=True,
    )
    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    quantidade = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Quantidade do produto nesta linha da venda.',
    )

    class Meta:
        db_table = 'loja_venda' # Aponta para a tua tabela real no MySQL

    @property
    def subtotal(self):
        preco = self.preco_unitario or (self.produto.preco if self.produto else Decimal('0.00'))
        return ((self.quantidade or 1) * (preco or Decimal('0.00'))).quantize(Decimal('0.01'))

    def __str__(self):
        return f"Venda {self.id_transacao} - {self.produto.nome}"

# 4.5. ZONAS DE ENTREGA (Frete configurável pelo administrador)
class ZonaEntrega(models.Model):
    nome = models.CharField(max_length=120, help_text="Nome da zona (ex: Zona 1 - Cacuaco e Viana)")
    taxa = models.DecimalField(max_digits=10, decimal_places=2, help_text="Taxa de entrega em Kwanzas (Kz)")
    descricao = models.CharField(max_length=255, blank=True, help_text="Bairros e municípios atendidos nesta zona")
    prazo_estimado = models.CharField(max_length=100, blank=True, default="No mesmo dia ou até 24h", help_text="Prazo estimado de entrega")
    ativo = models.BooleanField(default=True, help_text="Marque para manter esta zona ativa para escolha dos clientes")
    ordem = models.PositiveIntegerField(default=0, help_text="Ordem de exibição na lista (menor número aparece primeiro)")

    class Meta:
        verbose_name = "Zona de Entrega"
        verbose_name_plural = "Zonas de Entrega"
        ordering = ['ordem', 'taxa', 'nome']

    def __str__(self):
        return f"{self.nome} ({self.taxa:,.2f} Kz)".replace(',', 'X').replace('.', ',').replace('X', '.')


# 5. ESTRUTURA DE PEDIDOS (Para o processo de checkout)
class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Aguardando pagamento'
        PAID = 'paid', 'Pago'
        PROCESSING = 'processing', 'Em preparação'
        SHIPPED = 'shipped', 'Em transporte'
        DELIVERED = 'delivered', 'Entregue'
        FAILED = 'failed', 'Falhou'
        CANCELLED = 'cancelled', 'Cancelado'
        REFUNDED = 'refunded', 'Reembolsado'

    usuario = models.ForeignKey(User, on_delete=models.PROTECT, db_index=True)
    data_criacao = models.DateTimeField(auto_now_add=True, db_index=True)
    finalizado = models.BooleanField(default=False, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    frete = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    zona_entrega = models.ForeignKey(
        'ZonaEntrega',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos',
        verbose_name="Zona de Entrega",
    )
    endereco_entrega = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Endereço / Ponto de Referência",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    idempotency_key = models.UUIDField(
        unique=True,
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    @property
    def codigo_pedido(self):
        return f"MRC-PED-{self.id:06d}"

    @property
    def badge_status(self):
        mapa = {
            self.Status.PENDING_PAYMENT: {'label': 'Aguardando Pagamento', 'classe': 'bg-warning text-dark', 'icone': 'fas fa-clock'},
            self.Status.PAID: {'label': 'Pago', 'classe': 'bg-info text-dark', 'icone': 'fas fa-credit-card'},
            self.Status.PROCESSING: {'label': 'Em Preparação', 'classe': 'bg-primary', 'icone': 'fas fa-box-open'},
            self.Status.SHIPPED: {'label': 'Em Transporte', 'classe': 'bg-warning text-dark', 'icone': 'fas fa-truck-fast'},
            self.Status.DELIVERED: {'label': 'Entregue', 'classe': 'bg-success', 'icone': 'fas fa-circle-check'},
            self.Status.FAILED: {'label': 'Falhou', 'classe': 'bg-danger', 'icone': 'fas fa-circle-xmark'},
            self.Status.CANCELLED: {'label': 'Cancelado', 'classe': 'bg-secondary', 'icone': 'fas fa-ban'},
            self.Status.REFUNDED: {'label': 'Reembolsado', 'classe': 'bg-dark', 'icone': 'fas fa-rotate-left'},
        }
        return mapa.get(self.status, {'label': self.get_status_display(), 'classe': 'bg-secondary', 'icone': 'fas fa-receipt'})

    @property
    def is_interrompido(self):
        return self.status in {self.Status.CANCELLED, self.Status.FAILED, self.Status.REFUNDED}

    @property
    def percentual_progresso(self):
        progresso_map = {
            self.Status.PENDING_PAYMENT: 15,
            self.Status.PAID: 35,
            self.Status.PROCESSING: 60,
            self.Status.SHIPPED: 85,
            self.Status.DELIVERED: 100,
        }
        return progresso_map.get(self.status, 0)

    def obter_etapas_timeline(self):
        """Monta o progresso cronológico das 5 fases de entrega com timestamps reais."""
        historico_map = {
            h.status_novo: h.criado_em
            for h in self.historico_status.all().order_by('criado_em')
        }

        fases_normais = [
            (self.Status.PENDING_PAYMENT, 'Pedido Realizado', 'Pedido recebido com sucesso', 'fas fa-receipt'),
            (self.Status.PAID, 'Pagamento Confirmado', 'Pagamento aprovado pelo sistema', 'fas fa-credit-card'),
            (self.Status.PROCESSING, 'Em Preparação', 'Separação e conferência no armazém', 'fas fa-box-open'),
            (self.Status.SHIPPED, 'Em Transporte', 'Saiu para entrega ao destinatário', 'fas fa-truck-fast'),
            (self.Status.DELIVERED, 'Entregue', 'Entrega realizada com sucesso', 'fas fa-house-circle-check'),
        ]

        ordem_prioridade = {
            self.Status.PENDING_PAYMENT: 0,
            self.Status.PAID: 1,
            self.Status.PROCESSING: 2,
            self.Status.SHIPPED: 3,
            self.Status.DELIVERED: 4,
        }

        status_atual_idx = ordem_prioridade.get(self.status, 0)
        interrompido = self.is_interrompido

        etapas = []
        for idx, (st_key, titulo, desc, icone) in enumerate(fases_normais):
            data_etapa = historico_map.get(st_key)
            if idx == 0 and not data_etapa:
                data_etapa = self.data_criacao
            elif idx == 1 and not data_etapa:
                pagamento = getattr(self, 'pagamento', None)
                if pagamento and pagamento.status == Pagamento.Status.PAID:
                    data_etapa = pagamento.criado_em

            if interrompido:
                estado = 'completed' if data_etapa else 'upcoming'
            else:
                if idx < status_atual_idx:
                    estado = 'completed'
                elif idx == status_atual_idx:
                    estado = 'current'
                else:
                    estado = 'upcoming'

            etapas.append({
                'key': st_key,
                'titulo': titulo,
                'descricao': desc,
                'icone': icone,
                'estado': estado,
                'data_hora': data_etapa,
            })

        return etapas

    def __str__(self):
        return f"Pedido {self.id} - {self.usuario.username}"


class Pagamento(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        PAID = 'paid', 'Pago'
        FAILED = 'failed', 'Falhou'
        REFUNDED = 'refunded', 'Reembolsado'

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name='pagamento',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    provider = models.CharField(max_length=50, default='internal')
    provider_transaction_id = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
    )
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True, db_index=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    detalhes = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Pagamento do pedido {self.pedido_id} - {self.status}"


class MovimentacaoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        VENDA = 'venda', 'Venda'
        AJUSTE = 'ajuste', 'Ajuste'
        DEVOLUCAO = 'devolucao', 'Devolução'
        PERDA = 'perda', 'Perda'

    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='movimentacoes_estoque',
        db_index=True,
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    quantidade = models.IntegerField(help_text='Variação do estoque. Entradas são positivas e saídas negativas.')
    saldo_anterior = models.PositiveIntegerField()
    saldo_posterior = models.PositiveIntegerField()
    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimentacoes_estoque',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_estoque',
    )
    referencia = models.CharField(max_length=120, blank=True)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-criado_em', '-id')
        indexes = [
            models.Index(fields=('produto', 'criado_em'), name='loja_movime_produto_aa0bea_idx'),
            models.Index(fields=('tipo', 'criado_em'), name='loja_movime_tipo_4e4bc1_idx'),
        ]

    def __str__(self):
        return f'{self.produto.sku} {self.tipo} {self.quantidade:+d}'


class HistoricoStatusPedido(models.Model):
    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.PROTECT,
        related_name='historico_status',
    )
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alteracoes_status_pedido',
    )
    observacao = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-criado_em', '-id')

    def __str__(self):
        return f'Pedido {self.pedido_id}: {self.status_anterior or "inicial"} -> {self.status_novo}'


class AuditoriaAdministrativa(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias_administrativas',
    )
    acao = models.CharField(max_length=30, db_index=True)
    modelo = models.CharField(max_length=100, db_index=True)
    objeto_id = models.CharField(max_length=100, blank=True)
    alteracoes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-criado_em', '-id')
        indexes = [
            models.Index(fields=('modelo', 'objeto_id'), name='loja_audito_modelo_171f7c_idx'),
            models.Index(fields=('usuario', 'criado_em'), name='loja_audito_usuario_893585_idx'),
        ]

    def __str__(self):
        return f'{self.acao} {self.modelo} #{self.objeto_id}'


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='itens', on_delete=models.PROTECT, db_index=True)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, db_index=True)
    quantidade = models.PositiveIntegerField(default=1, db_index=True)
    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"
