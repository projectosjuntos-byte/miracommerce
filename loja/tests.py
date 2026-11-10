from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from .models import (
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
    ZonaEntrega,
)
from .checkout import processar_finalizacao_compra
from .recomendacoes import gerar_regras_associacao
from .services import obter_recomendacoes_para_produto
from .security import get_client_ip
from .tasks import (
    anonimizar_usuarios_inativos_task,
    atualizar_promocoes_task,
    gerar_regras_associacao_task,
    enviar_email_status_pedido_task,
)
from .notificacoes import (
    enviar_email_notificacao_status,
    gerar_link_whatsapp,
    gerar_link_whatsapp_cliente,
    gerar_link_whatsapp_suporte,
)


class ProdutoBusinessLogicTests(TestCase):
    def setUp(self):
        cache.clear()
        session = self.client.session
        session['guia_introducao_vista'] = True
        session.save()
        self.categoria = Categoria.objects.create(nome='Mercearia')
        self.produto = Produto.objects.create(
            nome='Arroz Premium',
            categoria=self.categoria,
            preco=Decimal('100.00'),
            quantidade_estoque=10,
            data_validade=date.today() + timedelta(days=30),
        )
        self.user = get_user_model().objects.create_user(
            username='cliente1',
            email='cliente1@email.com',
            password='senha123',
        )

    def test_promocao_automatica_por_validade(self):
        self.produto.aplicar_promocao_automatica()

        self.assertTrue(self.produto.em_promocao)
        self.assertTrue(self.produto.status_promocao)
        self.assertEqual(self.produto.preco_promocional, Decimal('80.00'))
        self.assertEqual(self.produto.obter_preco_venda(), Decimal('80.00'))

    def test_checkout_usa_preco_promocional_no_total(self):
        self.produto.aplicar_promocao_automatica()
        self.produto.save()

        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 2}
        session.save()
        self.client.force_login(self.user)

        carrinho_response = self.client.get(reverse('exibir_carrinho'))
        response = self.client.post('/finalizar-compra/', {
            'idempotency_key': carrinho_response.context['checkout_idempotency_key'],
        })
        self.produto.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.produto.quantidade_estoque, 8)
        venda = Venda.objects.get(usuario=self.user)
        self.assertEqual(Venda.objects.filter(usuario=self.user).count(), 1)
        self.assertEqual(venda.quantidade, 2)
        pedido = Pedido.objects.get(usuario=self.user)
        item = ItemPedido.objects.get(pedido=pedido, produto=self.produto)
        self.assertTrue(pedido.finalizado)
        self.assertEqual(pedido.subtotal, Decimal('160.00'))
        self.assertEqual(pedido.total, Decimal('160.00') + pedido.frete)
        self.assertEqual(item.preco_unitario, Decimal('80.00'))
        self.assertEqual(item.subtotal, Decimal('160.00'))
        perfil = Perfil.objects.get(usuario=self.user)
        self.assertEqual(perfil.saldo_bonus, Decimal('8.00'))
        self.assertEqual(perfil.total_compras_realizadas, 1)
        self.assertEqual(pedido.status, Pedido.Status.PAID)
        self.assertEqual(Pagamento.objects.get(pedido=pedido).status, Pagamento.Status.PAID)

    def test_checkout_idempotente_nao_duplica_pedido(self):
        chave = '2f8f705a-0f64-4de7-98d8-9ab5e48c4a0c'

        processar_finalizacao_compra(
            self.user,
            {str(self.produto.id): 1},
            idempotency_key=chave,
        )
        processar_finalizacao_compra(
            self.user,
            {str(self.produto.id): 1},
            idempotency_key=chave,
        )

        self.assertEqual(Pedido.objects.filter(usuario=self.user).count(), 1)
        self.assertEqual(Pagamento.objects.filter(pedido__usuario=self.user).count(), 1)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 9)

    def test_checkout_reutiliza_a_chave_para_abas_do_mesmo_carrinho(self):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 1}
        session.save()

        primeira_aba = self.client.get(reverse('exibir_carrinho'))
        segunda_aba = self.client.get(reverse('exibir_carrinho'))

        self.assertEqual(
            primeira_aba.context['checkout_idempotency_key'],
            segunda_aba.context['checkout_idempotency_key'],
        )

    def test_home_recarrega_preco_e_estoque_frescos_apos_cache(self):
        self.client.get('/')
        self.produto.quantidade_estoque = 0
        self.produto.save(update_fields=['quantidade_estoque'])

        response = self.client.get('/')

        self.assertContains(response, 'ESGOTADO')

    def test_edicao_ajax_do_carrinho_atualiza_totais_sem_redirecionar(self):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 2}
        session.save()

        response = self.client.post(
            reverse('editar_carrinho', args=[self.produto.id, 'aumentar']),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['quantidade'], 3)
        self.assertEqual(response.json()['item_subtotal'], '240.00')
        self.assertEqual(response.json()['total'], '240.00')
        self.assertEqual(self.client.session['carrinho'], {str(self.produto.id): 3})

    def test_checkout_exige_post(self):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 1}
        session.save()
        self.client.force_login(self.user)

        response = self.client.get('/finalizar-compra/')

        self.assertEqual(response.status_code, 405)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 10)
        self.assertFalse(Pedido.objects.filter(usuario=self.user).exists())

    def test_checkout_bloqueia_produto_vencido(self):
        self.produto.data_validade = date.today() - timedelta(days=1)
        self.produto.save()

        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 1}
        session.save()
        self.client.force_login(self.user)

        carrinho_response = self.client.get(reverse('exibir_carrinho'))
        response = self.client.post('/finalizar-compra/', {
            'idempotency_key': carrinho_response.context['checkout_idempotency_key'],
        })

        self.assertRedirects(response, '/carrinho/')
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 10)
        self.assertFalse(Pedido.objects.filter(usuario=self.user).exists())

    def test_promocao_manual_no_admin_persiste_na_vitrine(self):
        self.produto.data_validade = date.today() + timedelta(days=365)
        self.produto.em_promocao = True
        self.produto.preco_promocional = Decimal('75.00')
        self.produto.status_promocao = True
        self.produto.save()

        self.produto.aplicar_promocao_automatica()

        self.assertTrue(self.produto.em_promocao)
        self.assertTrue(self.produto.status_promocao)
        self.assertEqual(self.produto.preco_promocional, Decimal('75.00'))
        self.assertEqual(self.produto.obter_preco_venda(), Decimal('75.00'))

    def test_promocao_manual_sem_preco_promocional_gera_desconto_automatico(self):
        self.produto.em_promocao = True
        self.produto.preco_promocional = None
        self.produto.status_promocao = False
        self.produto.save()

        self.produto.aplicar_promocao_automatica()

        self.assertTrue(self.produto.em_promocao)
        self.assertTrue(self.produto.status_promocao)
        self.assertEqual(self.produto.preco_promocional, Decimal('80.00'))
        self.assertEqual(self.produto.obter_preco_venda(), Decimal('80.00'))

    def test_recomendacao_por_categoria_funciona_sem_vendas_previas(self):
        categoria = Categoria.objects.create(nome='Higiene e Casa')
        subcategoria = SubCategoria.objects.create(categoria=categoria, nome='Limpeza da Casa')
        produto = Produto.objects.create(
            nome='Detergente',
            categoria=categoria,
            subcategoria=subcategoria,
            preco=Decimal('120.00'),
            quantidade_estoque=5,
        )
        Produto.objects.create(
            nome='Esponja',
            categoria=categoria,
            subcategoria=subcategoria,
            preco=Decimal('30.00'),
            quantidade_estoque=10,
        )

        recomendacoes = obter_recomendacoes_para_produto(produto.nome)

        self.assertIn('Esponja', recomendacoes)

    def test_vitrine_exibe_subcategorias_no_menu(self):
        categoria = Categoria.objects.create(nome='Higiene e Casa')
        subcategoria = SubCategoria.objects.create(categoria=categoria, nome='Limpeza da Casa')
        Produto.objects.create(
            nome='Detergente',
            categoria=categoria,
            subcategoria=subcategoria,
            preco=Decimal('120.00'),
            quantidade_estoque=5,
        )

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Higiene e Casa')
        self.assertContains(response, 'Limpeza da Casa')

    def test_vitrine_filtra_por_subcategoria(self):
        categoria = Categoria.objects.create(nome='Higiene e Casa')
        sub1 = SubCategoria.objects.create(categoria=categoria, nome='Limpeza da Casa')
        sub2 = SubCategoria.objects.create(categoria=categoria, nome='Mundo Pet')
        Produto.objects.create(
            nome='Detergente',
            categoria=categoria,
            subcategoria=sub1,
            preco=Decimal('120.00'),
            quantidade_estoque=5,
        )
        Produto.objects.create(
            nome='Coleira para Cães',
            categoria=categoria,
            subcategoria=sub2,
            preco=Decimal('150.00'),
            quantidade_estoque=7,
        )

        response = self.client.get(f'/subcategoria/{sub1.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detergente')
        self.assertNotContains(response, 'Coleira para Cães')

    @override_settings(CATALOG_PAGE_SIZE=2)
    def test_vitrine_paginaa_catalogo_sem_carregar_todos_os_produtos(self):
        produtos = [
            Produto.objects.create(
                nome=f'Produto de página {indice}',
                categoria=self.categoria,
                preco=Decimal('10.00'),
                quantidade_estoque=5,
            )
            for indice in range(1, 5)
        ]

        response = self.client.get(reverse('home'), {'pagina': 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pagina_produtos'].number, 2)
        self.assertEqual(
            [produto.pk for produto in response.context['produtos']],
            [produtos[1].pk, produtos[2].pk],
        )
        self.assertContains(response, 'Página 2 de 3')

    def test_painel_calcula_valores_com_quantidade_por_linha_de_venda(self):
        gestor = get_user_model().objects.create_user(
            username='gestor_quantidade', password='SenhaForte#2026', is_staff=True,
        )
        Venda.objects.create(
            id_transacao=9001,
            produto=self.produto,
            usuario=self.user,
            preco_unitario=Decimal('100.00'),
            quantidade=3,
        )
        self.client.force_login(gestor)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.context['ticket_medio'], Decimal('300.00'))
        self.assertEqual(response.context['top_vendidos'][0]['total'], 3)


class GuideIntroTests(TestCase):
    def test_primeira_visita_a_home_abre_o_guia(self):
        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('guia'))
        self.assertTrue(self.client.session.get('guia_introducao_vista'))

    def test_visitas_seguintes_abrem_a_home(self):
        self.client.get(reverse('home'))

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'loja/index.html')

    def test_cta_do_guia_muda_apos_a_abertura_inicial(self):
        primeira_visita = self.client.get(reverse('home'))
        guia_inicial = self.client.get(primeira_visita.url)

        self.assertContains(guia_inicial, 'Ir à loja')

        guia_reaberto = self.client.get(reverse('guia'))
        self.assertContains(guia_reaberto, 'Voltar à loja')

    def test_link_do_guia_marca_a_introducao_como_vista(self):
        response = self.client.get(reverse('guia'))

        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)


class RecommendationRuleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username='regras', password='SenhaForte#2026')
        self.categoria = Categoria.objects.create(nome='Regras')
        self.produto_a = Produto.objects.create(
            nome='Produto A', categoria=self.categoria, preco=Decimal('10.00'), quantidade_estoque=10,
        )
        self.produto_b = Produto.objects.create(
            nome='Produto B', categoria=self.categoria, preco=Decimal('20.00'), quantidade_estoque=10,
        )
        self.produto_c = Produto.objects.create(
            nome='Produto C', categoria=self.categoria, preco=Decimal('30.00'), quantidade_estoque=10,
        )

    def criar_pedido_pago(self, *produtos):
        pedido = Pedido.objects.create(
            usuario=self.user,
            finalizado=True,
            status=Pedido.Status.PAID,
            subtotal=Decimal('0.00'),
            frete=Decimal('0.00'),
            total=Decimal('0.00'),
        )
        ItemPedido.objects.bulk_create([
            ItemPedido(
                pedido=pedido,
                produto=produto,
                quantidade=1,
                preco_unitario=produto.preco,
                subtotal=produto.preco,
            )
            for produto in produtos
        ])
        return pedido

    @override_settings(RECOMMENDATION_LOOKBACK_DAYS=0, RECOMMENDATION_MIN_LIFT=0)
    def test_regras_usam_itens_de_pedidos_sem_matriz_em_memoria(self):
        self.criar_pedido_pago(self.produto_a, self.produto_b)
        self.criar_pedido_pago(self.produto_a, self.produto_b)
        self.criar_pedido_pago(self.produto_a, self.produto_c)

        regras = gerar_regras_associacao(force_refresh=True)
        recomendacoes = obter_recomendacoes_para_produto(self.produto_a.id)

        self.assertTrue(regras)
        self.assertIn('Produto B', recomendacoes)
        self.assertNotIn('Produto A', recomendacoes)

    @override_settings(RECOMMENDATION_LOOKBACK_DAYS=0, RECOMMENDATION_MIN_LIFT=0)
    def test_regras_incluem_historico_legado_sem_pedido(self):
        for transacao in (1001, 1002):
            Venda.objects.create(
                id_transacao=transacao,
                produto=self.produto_a,
                usuario=self.user,
                preco_unitario=self.produto_a.preco,
            )
            Venda.objects.create(
                id_transacao=transacao,
                produto=self.produto_b,
                usuario=self.user,
                preco_unitario=self.produto_b.preco,
            )

        regras = gerar_regras_associacao(force_refresh=True)

        self.assertTrue(any(
            self.produto_a.id in regra['antecedents'] and self.produto_b.id in regra['consequents']
            for regra in regras
        ))


class ProxyHeaderSecurityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_ip_do_cliente_ignora_cabecalho_forjado_por_padrao(self):
        request = self.factory.post('/', REMOTE_ADDR='10.0.0.20', HTTP_X_REAL_IP='203.0.113.10')

        self.assertEqual(get_client_ip(request), '10.0.0.20')

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_ip_do_cliente_aceita_x_real_ip_apenas_com_proxy_configurado(self):
        request = self.factory.post('/', REMOTE_ADDR='10.0.0.20', HTTP_X_REAL_IP='203.0.113.10')

        self.assertEqual(get_client_ip(request), '203.0.113.10')


class HealthEndpointTests(TestCase):
    def test_liveness_endpoint(self):
        response = self.client.get('/health/live/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertTrue(response.headers['X-Request-ID'])
        self.assertGreaterEqual(float(response.headers['X-Response-Time-ms']), 0)

    def test_readiness_endpoint_verifica_dependencias(self):
        response = self.client.get('/health/ready/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})


class PublicInformationPagesTests(TestCase):
    def test_faq_e_definicoes_carregam(self):
        faq_response = self.client.get(reverse('faq'))
        settings_response = self.client.get(reverse('definicoes'))

        self.assertEqual(faq_response.status_code, 200)
        self.assertContains(faq_response, 'Perguntas frequentes')
        self.assertEqual(settings_response.status_code, 200)
        self.assertContains(settings_response, reverse('definicoes_privacidade'))
        self.assertContains(settings_response, reverse('politica_devolucao'))

    def test_politicas_estao_acessiveis(self):
        privacy_response = self.client.get(reverse('definicoes_privacidade'))
        return_response = self.client.get(reverse('politica_devolucao'))

        self.assertEqual(privacy_response.status_code, 200)
        self.assertContains(privacy_response, 'Política de privacidade')
        self.assertEqual(return_response.status_code, 200)
        self.assertContains(return_response, 'Política de devolução')


class AccountSettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='definicoes',
            email='antes@email.com',
            password='SenhaForte#2026',
            first_name='Nome',
            last_name='Anterior',
        )
        Perfil.objects.create(
            usuario=self.user,
            telefone='+244900000001',
            provincia='Luanda',
            municipio='Luanda',
            bairro='Maianga',
        )

    def test_definicoes_exibe_as_oito_configuracoes(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('definicoes'))

        self.assertEqual(response.status_code, 200)
        for texto in (
            'Alteração de idioma entre Português e English.',
            'Edição de nome e sobrenome.',
            'Edição de e-mail.',
            'Edição de telefone.',
            'Edição de província, município e bairro.',
            'Sair apenas da sessão atual.',
            'Encerrar o acesso à conta, mantendo os dados.',
            'Excluir dados pessoais e anonimizar a conta.',
        ):
            self.assertContains(response, texto)

    def test_usuario_atualiza_dados_endereco_e_idioma(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('atualizar_definicoes'), {
            'idioma': 'en',
            'first_name': 'Nome Novo',
            'last_name': 'Utilizador',
            'email': 'depois@email.com',
            'telefone': '+244900000002',
            'provincia': 'Benguela',
            'municipio': 'Lobito',
            'bairro': 'Restinga',
        })

        self.assertRedirects(response, reverse('definicoes'))
        self.user.refresh_from_db()
        perfil = Perfil.objects.get(usuario=self.user)
        self.assertEqual(self.user.get_full_name(), 'Nome Novo Utilizador')
        self.assertEqual(self.user.email, 'depois@email.com')
        self.assertEqual(perfil.idioma, 'en')
        self.assertEqual(perfil.telefone, '+244900000002')
        self.assertEqual(perfil.municipio, 'Lobito')
        self.assertEqual(response.cookies['django_language'].value, 'en')

        settings_response = self.client.get(reverse('definicoes'))
        self.assertContains(settings_response, 'Settings')
        self.assertNotContains(settings_response, 'Definições')

    def test_usuario_pode_encerrar_acesso_sem_apagar_dados(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('desativar_conta'))

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.email, 'antes@email.com')


class CadastroAndPasswordResetTests(TestCase):
    def cadastro_data(self, **overrides):
        data = {
            'username': 'novo_cliente',
            'password1': 'SenhaForte#2026',
            'password2': 'SenhaForte#2026',
            'first_name': 'Novo',
            'last_name': 'Cliente',
            'email': 'novo.cliente@email.com',
            'telefone': '+244900000000',
            'provincia': 'Luanda',
            'municipio': 'Luanda',
            'bairro': 'Maianga',
        }
        data.update(overrides)
        return data

    def test_cadastro_cria_usuario_perfil_e_inicia_sessao(self):
        response = self.client.post(reverse('cadastro'), self.cadastro_data())

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        usuario = get_user_model().objects.get(username='novo_cliente')
        perfil = Perfil.objects.get(usuario=usuario)

        self.assertEqual(usuario.email, 'novo.cliente@email.com')
        self.assertEqual(perfil.telefone, '+244900000000')
        self.assertEqual(perfil.provincia, 'Luanda')
        self.assertEqual(str(usuario.pk), self.client.session['_auth_user_id'])

    def test_cadastro_rejeita_senhas_diferentes_sem_criar_usuario(self):
        response = self.client.post(
            reverse('cadastro'),
            self.cadastro_data(password2='OutraSenha#2026'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(get_user_model().objects.filter(username='novo_cliente').exists())

    def test_cadastro_rejeita_username_duplicado(self):
        self.client.post(reverse('cadastro'), self.cadastro_data())
        self.client.logout()
        response = self.client.post(
            reverse('cadastro'),
            self.cadastro_data(email='outro.email@email.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Já existe uma conta com este nome de utilizador')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacao_de_senha_envia_email_e_altera_senha(self):
        usuario = get_user_model().objects.create_user(
            username='recuperar_cliente',
            email='recuperar@email.com',
            password='SenhaAntiga#2026',
        )

        response = self.client.post(
            reverse('password_reset'),
            {'email': usuario.email},
        )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('recuperar_cliente', mail.outbox[0].body)

        uidb64 = urlsafe_base64_encode(str(usuario.pk).encode())
        token = default_token_generator.make_token(usuario)
        confirm_url = reverse('password_reset_confirm', args=[uidb64, token])

        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/set-password/', response.url)

        set_password_url = reverse('password_reset_confirm', args=[uidb64, 'set-password'])
        response = self.client.post(
            set_password_url,
            {
                'new_password1': 'SenhaNova#2026',
                'new_password2': 'SenhaNova#2026',
            },
        )

        self.assertRedirects(response, reverse('password_reset_complete'))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('SenhaNova#2026'))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacao_de_senha_nao_revela_email_inexistente(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'nao-existe@email.com'},
        )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacao_de_senha_por_nome_de_utilizador(self):
        usuario = get_user_model().objects.create_user(
            username='cliente_reset_user',
            email='cliente.reset@exemplo.com',
            password='SenhaAntiga#2026',
        )

        response = self.client.post(
            reverse('password_reset'),
            {'email': 'cliente_reset_user'},
        )
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['cliente.reset@exemplo.com'])
        self.assertIn('cliente_reset_user', mail.outbox[0].body)
        self.assertIn('MiraComerce IA', mail.outbox[0].subject)
        self.assertGreater(len(mail.outbox[0].alternatives), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_comando_test_email_executa_com_sucesso(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('test_email', 'alvo@teste.com', stdout=out)
        self.assertIn('SUCESSO', out.getvalue())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alvo@teste.com'])

    @override_settings(AUTH_LOGIN_RATE_LIMIT=1)
    def test_login_tem_limite_de_tentativas(self):
        cache.clear()

        primeira = self.client.post(
            reverse('login'),
            {'username': 'cliente-inexistente', 'password': 'errada'},
        )
        segunda = self.client.post(
            reverse('login'),
            {'username': 'cliente-inexistente', 'password': 'errada'},
        )

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 429)
        self.assertEqual(segunda.headers['Retry-After'], '300')

    def test_login_aceita_email_da_conta(self):
        usuario = get_user_model().objects.create_user(
            username='login_por_email',
            email='login.por.email@example.com',
            password='SenhaForte#2026',
        )

        response = self.client.post(
            reverse('login'),
            {'username': usuario.email, 'password': 'SenhaForte#2026'},
        )

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertEqual(str(usuario.pk), self.client.session['_auth_user_id'])


class CheckoutFailureTests(TestCase):
    def setUp(self):
        cache.clear()
        self.categoria = Categoria.objects.create(nome='Checkout')
        self.produto = Produto.objects.create(
            nome='Produto de Checkout',
            categoria=self.categoria,
            preco=Decimal('100.00'),
            quantidade_estoque=2,
            data_validade=date.today() + timedelta(days=30),
        )
        self.usuario = get_user_model().objects.create_user(
            username='checkout_cliente',
            email='checkout@email.com',
            password='SenhaForte#2026',
        )

    def test_checkout_falha_por_estoque_sem_criar_pedido(self):
        with self.assertRaisesMessage(ValueError, 'Estoque insuficiente'):
            processar_finalizacao_compra(
                self.usuario,
                {str(self.produto.id): 3},
            )

        self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 2)

    def test_checkout_rejeita_quantidade_invalida(self):
        with self.assertRaisesMessage(ValueError, 'Quantidade inválida'):
            processar_finalizacao_compra(
                self.usuario,
                {str(self.produto.id): 0},
            )

        self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())

    @override_settings(SIMULATED_PAYMENTS_ENABLED=False)
    def test_checkout_nao_confirma_pagamento_simulado_em_producao(self):
        with self.assertRaisesMessage(ValueError, 'pagamento ainda não foi confirmado'):
            processar_finalizacao_compra(
                self.usuario,
                {str(self.produto.id): 1},
            )

        self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 2)

    def test_checkout_reverte_transacao_se_registro_de_venda_falhar(self):
        with patch('loja.checkout.Venda.objects.bulk_create', side_effect=RuntimeError('falha de persistência')):
            with self.assertRaisesMessage(RuntimeError, 'falha de persistência'):
                processar_finalizacao_compra(
                    self.usuario,
                    {str(self.produto.id): 1},
                )

        self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())
        self.assertFalse(ItemPedido.objects.exists())
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 2)

    def test_checkout_reverte_transacao_se_pagamento_falhar(self):
        with patch(
            'loja.checkout.Pagamento.objects.create',
            side_effect=RuntimeError('falha no pagamento'),
        ):
            with self.assertRaisesMessage(RuntimeError, 'falha no pagamento'):
                processar_finalizacao_compra(
                    self.usuario,
                    {str(self.produto.id): 1},
                )

        self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())
        self.assertFalse(Pagamento.objects.exists())
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 2)

    @override_settings(
        FRETE_GRATIS_MINIMO=Decimal('25000.00'),
        FRETE_PADRAO=Decimal('1000.00'),
    )
    def test_checkout_calcula_frete_configuravel(self):
        self.produto.data_validade = date.today() + timedelta(days=365)
        self.produto.save(update_fields=['data_validade'])

        processar_finalizacao_compra(
            self.usuario,
            {str(self.produto.id): 1},
        )

        pedido = Pedido.objects.get(usuario=self.usuario)
        pagamento = Pagamento.objects.get(pedido=pedido)
        self.assertEqual(pedido.subtotal, Decimal('100.00'))
        self.assertEqual(pedido.frete, Decimal('1000.00'))
        self.assertEqual(pedido.total, Decimal('1100.00'))
        self.assertEqual(pagamento.valor, Decimal('1100.00'))
        movimento = MovimentacaoEstoque.objects.get(produto=self.produto, tipo=MovimentacaoEstoque.Tipo.VENDA)
        self.assertEqual(movimento.quantidade, -1)
        self.assertEqual(movimento.saldo_anterior, 2)
        self.assertEqual(movimento.saldo_posterior, 1)
        self.assertEqual(
            HistoricoStatusPedido.objects.get(pedido=pedido).status_novo,
            Pedido.Status.PAID,
        )


class AsyncBusinessTaskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.categoria = Categoria.objects.create(nome='Tarefas')
        self.produto = Produto.objects.create(
            nome='Produto próximo da validade',
            categoria=self.categoria,
            preco=Decimal('100.00'),
            quantidade_estoque=5,
            data_validade=date.today() + timedelta(days=10),
        )

    def test_tarefa_atualiza_promocoes_fora_da_requisicao(self):
        resultado = atualizar_promocoes_task.apply().get()

        self.assertEqual(resultado, 1)
        self.produto.refresh_from_db()
        self.assertTrue(self.produto.em_promocao)
        self.assertEqual(self.produto.preco_promocional, Decimal('80.00'))

    def test_tarefa_de_recomendacoes_nao_exige_vendas(self):
        resultado = gerar_regras_associacao_task.apply().get()

        self.assertEqual(resultado, 0)

    @override_settings(DATA_RETENTION_DAYS=365)
    @patch('loja.tasks.anonimizar_usuarios_inativos')
    def test_tarefa_de_anonimizacao_usa_retencao_configurada(self, anonimizar):
        anonimizar.return_value = 3

        resultado = anonimizar_usuarios_inativos_task.apply().get()

        self.assertEqual(resultado, 3)
        anonimizar.assert_called_once_with(dias=365)


class ProdutoImageUploadTests(TestCase):
    def setUp(self):
        cache.clear()
        self.categoria = Categoria.objects.create(nome='Imagens')

    @staticmethod
    def imagem_png(nome='produto.png', tamanho=(2, 2)):
        buffer = BytesIO()
        Image.new('RGB', tamanho, color='orange').save(buffer, format='PNG')
        return SimpleUploadedFile(nome, buffer.getvalue(), content_type='image/png')

    def produto_form_data(self):
        return {
            'nome': 'Produto com Imagem',
            'categoria': self.categoria.pk,
            'subcategoria': '',
            'preco': '100.00',
            'quantidade_estoque': '5',
            'data_validade': '',
            'status_promocao': '',
            'preco_promocional': '',
            'em_promocao': '',
        }

    def test_upload_de_imagem_valida_e_salva_em_produtos(self):
        ProdutoForm = modelform_factory(Produto, fields='__all__')

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            form = ProdutoForm(
                data=self.produto_form_data(),
                files={'imagem': self.imagem_png()},
            )

            self.assertTrue(form.is_valid(), form.errors)
            produto = form.save()

            self.assertTrue(produto.imagem.name.startswith('produtos/'))
            self.assertTrue(default_storage.exists(produto.imagem.name))
            produto.refresh_from_db()
            self.assertTrue(produto.thumbnail.name.startswith('produtos/thumbnails/'))
            self.assertTrue(default_storage.exists(produto.thumbnail.name))

    def test_upload_rejeita_arquivo_que_nao_e_imagem(self):
        ProdutoForm = modelform_factory(Produto, fields='__all__')
        arquivo_invalido = SimpleUploadedFile(
            'produto.png',
            b'conteudo que nao e uma imagem',
            content_type='image/png',
        )

        form = ProdutoForm(
            data=self.produto_form_data(),
            files={'imagem': arquivo_invalido},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('imagem', form.errors)

    def test_upload_rejeita_dimensoes_excessivas(self):
        ProdutoForm = modelform_factory(Produto, fields='__all__')
        form = ProdutoForm(
            data=self.produto_form_data(),
            files={'imagem': self.imagem_png(tamanho=(4001, 1))},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('imagem', form.errors)

    def test_alteracao_de_imagem_atualiza_thumbnail_automaticamente(self):
        ProdutoForm = modelform_factory(Produto, fields='__all__')

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            form1 = ProdutoForm(
                data=self.produto_form_data(),
                files={'imagem': self.imagem_png(nome='foto1.png')},
            )
            self.assertTrue(form1.is_valid(), form1.errors)
            produto = form1.save()
            produto.refresh_from_db()
            thumb1 = produto.thumbnail.name
            self.assertTrue(thumb1.startswith('produtos/thumbnails/'))

            form2 = ProdutoForm(
                data=self.produto_form_data(),
                files={'imagem': self.imagem_png(nome='foto2.png')},
                instance=produto,
            )
            self.assertTrue(form2.is_valid(), form2.errors)
            produto_atualizado = form2.save()
            produto_atualizado.refresh_from_db()

            thumb2 = produto_atualizado.thumbnail.name
            self.assertNotEqual(thumb1, thumb2)
            self.assertTrue(thumb2.startswith('produtos/thumbnails/'))
            self.assertTrue(default_storage.exists(thumb2))
            self.assertFalse(default_storage.exists(thumb1))

    def test_remocao_de_imagem_limpa_thumbnail_automaticamente(self):
        ProdutoForm = modelform_factory(Produto, fields='__all__')

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            form = ProdutoForm(
                data=self.produto_form_data(),
                files={'imagem': self.imagem_png()},
            )
            self.assertTrue(form.is_valid(), form.errors)
            produto = form.save()
            produto.refresh_from_db()
            thumb = produto.thumbnail.name
            self.assertTrue(default_storage.exists(thumb))

            # Remove a imagem
            produto.imagem = None
            produto.save()
            produto.refresh_from_db()

            self.assertFalse(bool(produto.thumbnail))
            self.assertFalse(default_storage.exists(thumb))


class ReportsAndPrivacyTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='gestor', email='gestor@email.com', password='SenhaForte#2026', is_staff=True,
        )
        self.user = get_user_model().objects.create_user(
            username='privacidade', email='pessoa@email.com', password='SenhaForte#2026',
            first_name='Pessoa', last_name='Utilizadora',
        )
        self.categoria = Categoria.objects.create(nome='Relatórios')
        self.produto = Produto.objects.create(nome='Café Arábica', categoria=self.categoria, preco=Decimal('150.00'), quantidade_estoque=5)

    def criar_venda(self, quando, transacao):
        venda = Venda.objects.create(
            id_transacao=transacao, produto=self.produto, usuario=self.user, preco_unitario=Decimal('150.00'),
        )
        Venda.objects.filter(pk=venda.pk).update(data_venda=quando)
        return venda

    def test_relatorio_filtra_por_periodo_e_pagina(self):
        agora = timezone.now()
        self.criar_venda(agora - timedelta(days=2), 101)
        self.criar_venda(agora - timedelta(days=20), 102)
        self.client.force_login(self.staff)

        response = self.client.get(reverse('relatorio_vendas'), {
            'inicio': (agora.date() - timedelta(days=3)).isoformat(),
            'fim': agora.date().isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '101')
        self.assertNotContains(response, '102')

    def test_relatorio_exporta_csv_excel_e_pdf(self):
        self.criar_venda(timezone.now(), 201)
        self.client.force_login(self.staff)

        csv_response = self.client.get(reverse('exportar_relatorio_vendas', args=['csv']))
        excel_response = self.client.get(reverse('exportar_relatorio_vendas', args=['excel']))
        pdf_response = self.client.get(reverse('exportar_relatorio_vendas', args=['pdf']))

        self.assertEqual(csv_response.status_code, 200)
        self.assertIn('Produto', csv_response.content.decode('utf-8-sig'))
        self.assertEqual(excel_response['Content-Type'], 'application/vnd.ms-excel; charset=utf-8')
        self.assertIn(b'<Workbook', excel_response.content)
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b'%PDF'))

    def test_usuario_pode_exportar_dados(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('exportar_dados'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('pessoa@email.com', response.content.decode('utf-8'))
        self.assertIn('attachment;', response['Content-Disposition'])

    def test_usuario_pode_solicitar_anonimizacao(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('excluir_dados'))

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.email.endswith('@anon.invalid'))
        self.assertFalse(self.user.has_usable_password())
        self.assertFalse(self.client.session.get('_auth_user_id'))


class OrderTrackingTests(TestCase):
    def setUp(self):
        UserModel = get_user_model()
        self.user = UserModel.objects.create_user('cliente1', 'cliente1@exemplo.com', 'SenhaForte123!')
        self.outro_user = UserModel.objects.create_user('cliente2', 'cliente2@exemplo.com', 'SenhaForte123!')
        self.staff = UserModel.objects.create_user('admin1', 'admin1@exemplo.com', 'SenhaForte123!', is_staff=True)

        self.produto = Produto.objects.create(
            nome='Arroz Bom Gosto',
            preco=Decimal('5000.00'),
            quantidade_estoque=20,
        )

        self.pedido = Pedido.objects.create(
            usuario=self.user,
            subtotal=Decimal('10000.00'),
            frete=Decimal('0.00'),
            total=Decimal('10000.00'),
            finalizado=True,
            status=Pedido.Status.PAID,
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=2,
            preco_unitario=Decimal('5000.00'),
            subtotal=Decimal('10000.00'),
        )
        Pagamento.objects.create(
            pedido=self.pedido,
            status=Pagamento.Status.PAID,
            provider='internal',
            valor=Decimal('10000.00'),
        )

    def test_meus_pedidos_requer_login(self):
        response = self.client.get(reverse('meus_pedidos'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('meus_pedidos')}")

    def test_meus_pedidos_lista_apenas_pedidos_do_usuario(self):
        self.client.force_login(self.user)
        Pedido.objects.create(
            usuario=self.outro_user,
            subtotal=Decimal('2000.00'),
            total=Decimal('2000.00'),
            status=Pedido.Status.PAID,
        )

        response = self.client.get(reverse('meus_pedidos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pedido.codigo_pedido)
        self.assertEqual(len(response.context['pagina_pedidos'].object_list), 1)

    def test_meus_pedidos_staff_enxerga_pedidos_dos_clientes(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('meus_pedidos'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['modo_ver_todos'])
        self.assertContains(response, self.pedido.codigo_pedido)
        self.assertContains(response, 'Gestão de Pedidos da Loja')

    def test_meus_pedidos_staff_pode_alternar_para_compras_pessoais(self):
        self.client.force_login(self.staff)
        response = self.client.get(f"{reverse('meus_pedidos')}?modo=meus")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['modo_ver_todos'])
        self.assertEqual(len(response.context['pagina_pedidos'].object_list), 0)

    def test_detalhe_pedido_renderiza_timeline_e_etapas(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('detalhe_pedido', args=[self.pedido.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pedido.codigo_pedido)
        self.assertContains(response, 'Arroz Bom Gosto')
        self.assertContains(response, 'Rastreio de Pedido')

        etapas = response.context['etapas']
        self.assertEqual(len(etapas), 5)
        self.assertEqual(etapas[0]['key'], Pedido.Status.PENDING_PAYMENT)
        self.assertEqual(etapas[0]['estado'], 'completed')
        self.assertEqual(etapas[1]['key'], Pedido.Status.PAID)
        self.assertEqual(etapas[1]['estado'], 'current')

    def test_usuario_nao_pode_acessar_pedido_de_outro(self):
        self.client.force_login(self.outro_user)
        response = self.client.get(reverse('detalhe_pedido', args=[self.pedido.id]))
        self.assertEqual(response.status_code, 404)

    def test_staff_pode_acessar_pedido_de_qualquer_usuario(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('detalhe_pedido', args=[self.pedido.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pedido.codigo_pedido)

    def test_transicao_de_status_gera_historico_automatico(self):
        self.pedido.status = Pedido.Status.PROCESSING
        self.pedido.save()

        historicos = list(self.pedido.historico_status.all().order_by('criado_em'))
        status_registrados = [h.status_novo for h in historicos]
        self.assertIn(Pedido.Status.PAID, status_registrados)
        self.assertIn(Pedido.Status.PROCESSING, status_registrados)

        etapas = self.pedido.obter_etapas_timeline()
        self.assertEqual(etapas[0]['estado'], 'completed')
        self.assertEqual(etapas[1]['estado'], 'completed')
        self.assertEqual(etapas[2]['estado'], 'current')
        self.assertEqual(etapas[3]['estado'], 'upcoming')
        self.assertEqual(etapas[4]['estado'], 'upcoming')

    def test_staff_dashboard_renderiza_metricas_completas_e_pedidos(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Central de Gestão MiraComerce')
        self.assertContains(response, 'Faturamento Total')
        self.assertContains(response, 'Últimos Pedidos dos Clientes')
        self.assertContains(response, self.pedido.codigo_pedido)
        self.assertIn('pedidos_recentes', response.context)
        self.assertIn('total_receita', response.context)

    def test_staff_dashboard_modo_vitrine(self):
        self.client.force_login(self.staff)
        response = self.client.get(f"{reverse('home')}?modo_vitrine=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modo Vitrine Ativo')
        self.assertContains(response, 'Voltar ao Painel da Operação')

    def test_detalhe_pedido_inclui_links_whatsapp_e_painel_staff(self):
        Perfil.objects.create(usuario=self.user, telefone='923112233', bairro='Camama', municipio='Talatona')
        self.client.force_login(self.user)
        response = self.client.get(reverse('detalhe_pedido', args=[self.pedido.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('whatsapp_link_suporte', response.context)
        self.assertIn('https://wa.me/', response.context['whatsapp_link_suporte'])
        # Cliente comum não deve ver a barra de operações staff
        self.assertNotContains(response, 'Operações Staff')

        # Staff acessando
        self.client.force_login(self.staff)
        response_staff = self.client.get(reverse('detalhe_pedido', args=[self.pedido.id]))
        self.assertEqual(response_staff.status_code, 200)
        self.assertContains(response_staff, 'Operações Staff')
        self.assertContains(response_staff, 'Atualizar Estado')
        self.assertIn('whatsapp_link_cliente', response_staff.context)
        self.assertIn('244923112233', response_staff.context['whatsapp_link_cliente'])

    def test_staff_alterar_status_pedido(self):
        url = reverse('alterar_status_pedido_staff', args=[self.pedido.id])

        # Usuário não-staff é bloqueado
        self.client.force_login(self.user)
        response_user = self.client.post(url, {'novo_status': Pedido.Status.PROCESSING})
        self.assertRedirects(response_user, reverse('detalhe_pedido', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.Status.PAID)

        # Staff altera status com sucesso
        self.client.force_login(self.staff)
        response_staff = self.client.post(url, {'novo_status': Pedido.Status.PROCESSING})
        self.assertRedirects(response_staff, reverse('detalhe_pedido', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.Status.PROCESSING)

        # Status inválido é rejeitado
        response_invalido = self.client.post(url, {'novo_status': 'status_inexistente'})
        self.assertRedirects(response_invalido, reverse('detalhe_pedido', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.Status.PROCESSING)

    def test_enviar_email_notificacao_status_completo(self):
        Perfil.objects.create(usuario=self.user, telefone='923112233', bairro='Camama', municipio='Talatona', provincia='Luanda')
        mail.outbox.clear()

        sucesso = enviar_email_notificacao_status(
            pedido_id=self.pedido.id,
            status_novo=Pedido.Status.SHIPPED,
            status_anterior=Pedido.Status.PROCESSING,
            site_url='https://miracommerce.ao'
        )
        self.assertTrue(sucesso)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertIn(self.user.email, email.to)
        self.assertIn(self.pedido.codigo_pedido, email.subject)
        self.assertIn('Pedido Enviado', email.subject)

        # Verifica corpo texto puro
        self.assertIn(self.pedido.codigo_pedido, email.body)
        self.assertIn('10.000,00 Kz', email.body)
        self.assertIn('https://miracommerce.ao', email.body)

        # Verifica anexo HTML
        self.assertEqual(len(email.alternatives), 1)
        html_content, mimetype = email.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('Arroz Bom Gosto', html_content)
        self.assertIn('10.000,00 Kz', html_content)
        self.assertIn('Camama', html_content)

    def test_notificacao_status_whatsapp_links_formatacao(self):
        link_angola = gerar_link_whatsapp('923456789', 'Olá teste')
        self.assertTrue(link_angola.startswith('https://wa.me/244923456789?text='))
        self.assertIn('Ol%C3%A1%20teste', link_angola)

        link_vazio = gerar_link_whatsapp('', 'teste')
        self.assertEqual(link_vazio, '')

        link_suporte = gerar_link_whatsapp_suporte(self.pedido)
        self.assertIn(self.pedido.codigo_pedido, link_suporte)

    def test_task_celery_enviar_email_status(self):
        mail.outbox.clear()
        res = enviar_email_status_pedido_task.apply(
            args=[self.pedido.id, Pedido.Status.DELIVERED, Pedido.Status.SHIPPED]
        )
        self.assertTrue(res.result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Entregue', mail.outbox[0].subject)


class VitrineFiltrosEOrdenacaoTests(TestCase):
    def setUp(self):
        cache.clear()
        session = self.client.session
        session['guia_introducao_vista'] = True
        session.save()

        self.cat_bebidas = Categoria.objects.create(nome='Bebidas', slug='bebidas')
        self.cat_mercearia = Categoria.objects.create(nome='Mercearia', slug='mercearia-e-despensa')

        self.p_agua = Produto.objects.create(
            nome='Agua Mineral 1.5L',
            categoria=self.cat_bebidas,
            preco=Decimal('500.00'),
            quantidade_estoque=50,
        )
        self.p_suco = Produto.objects.create(
            nome='Suco Natural Laranja',
            categoria=self.cat_bebidas,
            preco=Decimal('2000.00'),
            quantidade_estoque=20,
        )
        self.p_arroz = Produto.objects.create(
            nome='Arroz Agulha 5kg',
            categoria=self.cat_mercearia,
            preco=Decimal('8000.00'),
            quantidade_estoque=15,
        )
        self.p_azeite = Produto.objects.create(
            nome='Azeite Extra Virgem',
            categoria=self.cat_mercearia,
            preco=Decimal('15000.00'),
            em_promocao=True,
            preco_promocional=Decimal('12000.00'),
            quantidade_estoque=10,
        )

    def test_ordenacao_menor_preco(self):
        response = self.client.get(f"{reverse('home')}?ordenar=menor_preco")
        self.assertEqual(response.status_code, 200)
        produtos = list(response.context['produtos'])
        ids = [p.id for p in produtos]
        self.assertEqual(ids, [self.p_agua.id, self.p_suco.id, self.p_arroz.id, self.p_azeite.id])

    def test_ordenacao_maior_preco(self):
        response = self.client.get(f"{reverse('home')}?ordenar=maior_preco")
        self.assertEqual(response.status_code, 200)
        produtos = list(response.context['produtos'])
        ids = [p.id for p in produtos]
        self.assertEqual(ids, [self.p_azeite.id, self.p_arroz.id, self.p_suco.id, self.p_agua.id])

    def test_ordenacao_nome_asc_e_desc(self):
        # A a Z
        response_asc = self.client.get(f"{reverse('home')}?ordenar=nome_asc")
        self.assertEqual(response_asc.status_code, 200)
        produtos_asc = list(response_asc.context['produtos'])
        self.assertEqual(produtos_asc[0].id, self.p_agua.id)
        self.assertEqual(produtos_asc[-1].id, self.p_suco.id)

        # Z a A
        response_desc = self.client.get(f"{reverse('home')}?ordenar=nome_desc")
        self.assertEqual(response_desc.status_code, 200)
        produtos_desc = list(response_desc.context['produtos'])
        self.assertEqual(produtos_desc[0].id, self.p_suco.id)
        self.assertEqual(produtos_desc[-1].id, self.p_agua.id)

    def test_ordenacao_em_promocao_prioriza_ofertas(self):
        response = self.client.get(f"{reverse('home')}?ordenar=em_promocao")
        self.assertEqual(response.status_code, 200)
        produtos = list(response.context['produtos'])
        self.assertTrue(produtos[0].em_promocao)
        self.assertEqual(produtos[0].id, self.p_azeite.id)

    def test_filtro_faixa_de_preco_min_e_max(self):
        response = self.client.get(f"{reverse('home')}?preco_min=1000&preco_max=10000")
        self.assertEqual(response.status_code, 200)
        ids = [p.id for p in response.context['produtos']]
        self.assertIn(self.p_suco.id, ids)
        self.assertIn(self.p_arroz.id, ids)
        self.assertNotIn(self.p_agua.id, ids)
        self.assertNotIn(self.p_azeite.id, ids)

    def test_filtro_apenas_promocao(self):
        response = self.client.get(f"{reverse('home')}?promo=1")
        self.assertEqual(response.status_code, 200)
        produtos = list(response.context['produtos'])
        self.assertEqual(len(produtos), 1)
        self.assertEqual(produtos[0].id, self.p_azeite.id)

    def test_filtro_combinado_categoria_e_preco(self):
        url = reverse('categoria_filtro', args=[self.cat_bebidas.id])
        response = self.client.get(f"{url}?preco_max=1000")
        self.assertEqual(response.status_code, 200)
        ids = [p.id for p in response.context['produtos']]
        self.assertEqual(ids, [self.p_agua.id])

    def test_contexto_inclui_filtros_ativos_presets_e_querystring(self):
        response = self.client.get(f"{reverse('home')}?preco_min=5000&preco_max=15000&ordenar=menor_preco")
        self.assertEqual(response.status_code, 200)
        self.assertIn('presets_preco', response.context)
        self.assertIn('filtros_ativos', response.context)
        self.assertIn('total_produtos', response.context)
        self.assertEqual(response.context['total_produtos'], 2)

        self.assertContains(response, 'catalog-controls-card')
        self.assertContains(response, 'id="id_ordenar"')
        self.assertContains(response, 'id="id_preco_min"')
        self.assertContains(response, 'id="id_preco_max"')
        self.assertContains(response, 'id="id_promo_toggle"')
        self.assertContains(response, 'Faixas rápidas:')

    def test_estado_vazio_quando_nenhum_produto_corresponde(self):
        response = self.client.get(f"{reverse('home')}?preco_min=999999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['produtos']), 0)
        self.assertContains(response, 'Nenhum produto encontrado')
        self.assertContains(response, 'Limpar Filtros e Ver Todos')


class ZonaEntregaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='cliente_entrega',
            email='cliente@exemplo.com',
            password='senha-forte-123',
        )
        self.produto = Produto.objects.create(
            nome='Arroz 5kg',
            preco=Decimal('5000.00'),
            quantidade_estoque=10,
            data_validade=date.today() + timedelta(days=365),
        )
        self.client.force_login(self.user)

    def test_zonas_padrao_carregadas_e_ordenadas(self):
        zonas = list(ZonaEntrega.objects.filter(ativo=True).order_by('ordem'))
        self.assertGreaterEqual(len(zonas), 3)
        self.assertEqual(zonas[0].taxa, Decimal('4000.00'))
        self.assertEqual(zonas[1].taxa, Decimal('2500.00'))
        self.assertEqual(zonas[2].taxa, Decimal('1500.00'))

    def test_carrinho_exibe_seletor_de_zonas(self):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 1}
        session.save()

        response = self.client.get(reverse('exibir_carrinho'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('zonas_disponiveis', response.context)
        self.assertIn('zona_selecionada', response.context)
        self.assertContains(response, 'id="zona-entrega-select"')
        self.assertContains(response, 'Zona 1')

    def test_endpoint_ajax_definir_zona_entrega(self):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 1}
        session.save()

        zona2 = ZonaEntrega.objects.filter(taxa=Decimal('2500.00')).first()
        self.assertIsNotNone(zona2)

        response = self.client.post(
            reverse('definir_zona_entrega'),
            {'zona_id': zona2.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados['ok'])
        self.assertEqual(dados['frete'], '2500.00')
        self.assertEqual(dados['total'], '7500.00')
        self.assertEqual(self.client.session.get('zona_entrega_id'), zona2.id)

    def test_finalizar_compra_grava_zona_e_endereco_no_pedido(self):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): 1}
        session.save()

        zona3 = ZonaEntrega.objects.filter(taxa=Decimal('1500.00')).first()
        carrinho_response = self.client.get(reverse('exibir_carrinho'))
        key = carrinho_response.context['checkout_idempotency_key']

        response = self.client.post(reverse('finalizar_compra'), {
            'idempotency_key': key,
            'zona_entrega_id': zona3.id,
            'endereco_entrega': 'Mutamba, Rua da Alfândega, Prédio 4, Apt 2',
        })
        self.assertEqual(response.status_code, 302)

        pedido = Pedido.objects.filter(usuario=self.user).latest('data_criacao')
        self.assertEqual(pedido.zona_entrega, zona3)
        self.assertEqual(pedido.frete, Decimal('1500.00'))
        self.assertEqual(pedido.total, Decimal('6500.00'))
        self.assertIn('Mutamba', pedido.endereco_entrega)

