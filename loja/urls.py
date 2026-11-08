from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .security import rate_limit


urlpatterns = [
    # --- Navegação Principal ---
    path('', views.home, name='home'),
    
    # Filtros de Categoria e Subcategoria para o algoritmo Apriori
    path('categoria/<int:categoria_id>/', views.home, name='categoria_filtro'),
    path('subcategoria/<int:subcategoria_id>/', views.home, name='subcategoria_filtro'),

    path('sobre/', views.sobre, name='sobre'),
    path('ajuda/', views.ajuda, name='ajuda'),
    path('faq/', views.faq, name='faq'),
    path('definicoes/', views.definicoes, name='definicoes'),
    path('definicoes/atualizar/', views.atualizar_definicoes, name='atualizar_definicoes'),
    path('definicoes/desativar-conta/', views.desativar_conta, name='desativar_conta'),
    path('definicoes/privacidade/', views.privacidade, name='definicoes_privacidade'),
    path('definicoes/devolucao/', views.politica_devolucao, name='politica_devolucao'),
    path('guia/', views.guia, name='guia'),
    
    # --- Relatórios e Inteligência de Dados (TCC) ---
    path('relatorios/vendas/', views.relatorio_vendas, name='relatorio_vendas'),
    path('relatorio-pdf/', lambda request: views.exportar_relatorio_vendas(request, 'pdf'), name='gerar_pdf_vendas'),
    path('relatorios/vendas/exportar/<str:formato>/', views.exportar_relatorio_vendas, name='exportar_relatorio_vendas'),
    path('privacidade/', views.privacidade, name='privacidade'),
    path('privacidade/exportar/', views.exportar_dados, name='exportar_dados'),
    path('privacidade/excluir/', views.excluir_dados, name='excluir_dados'),

    # --- Gestão do Carrinho ---
    path('carrinho/', views.exibir_carrinho, name='exibir_carrinho'),
    path('carrinho/add/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/remover/<int:produto_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('carrinho/editar/<int:produto_id>/<str:acao>/', views.editar_carrinho, name='editar_carrinho'),

    # --- Autenticação e Perfil ---
    path('cadastro/', views.cadastro, name='cadastro'),
    
    # IMPORTANTE: O nome da rota deve ser 'login' para o @login_required funcionar
    path(
        'login/',
        rate_limit(
            'login',
            'AUTH_LOGIN_RATE_LIMIT',
            window=300,
            subject_field='username',
        )(auth_views.LoginView.as_view(template_name='loja/login.html')),
        name='login',
    ),
    
    # Logout (Django 5.0+ exige método POST no template para logout)
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # --- Checkout e Finalização ---
    # Esta view deve ter o decorador @login_required no views.py
    path('finalizar-compra/', views.processar_finalizacao_compra, name='finalizar_compra'),

    # --- Rastreio e Gestão de Pedidos ---
    path('pedidos/', views.meus_pedidos, name='meus_pedidos'),
    path('pedidos/<int:pedido_id>/', views.detalhe_pedido, name='detalhe_pedido'),
    path('pedidos/<int:pedido_id>/alterar-status/', views.alterar_status_pedido_staff, name='alterar_status_pedido_staff'),

    # --- Ciclo de Recuperação de Senha Completo ---
    # 1. Formulário inicial para solicitar o link (Onde o usuário digita o e-mail)
    path(
        'password_reset/',
        rate_limit(
            'password-reset',
            'AUTH_PASSWORD_RESET_RATE_LIMIT',
            window=900,
            subject_field='email',
        )(auth_views.PasswordResetView.as_view(template_name="loja/password_reset_form.html")),
        name='password_reset',
    ),

    # 2. Página avisando que o e-mail foi enviado (Usando o seu recuperar_senha.html)
    path('password_reset/done/', 
        auth_views.PasswordResetDoneView.as_view(template_name="loja/recuperar_senha.html"), 
        name='password_reset_done'),

    # 3. Página onde o usuário define a nova senha (Link recebido no e-mail)
    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(template_name="loja/password_reset_confirm.html"), 
        name='password_reset_confirm'),
    
    # 4. Página final confirmando que a alteração foi concluída com sucesso
    path('reset/done/', 
        auth_views.PasswordResetCompleteView.as_view(template_name="loja/password_reset_complete.html"), 
        name='password_reset_complete'),
]
