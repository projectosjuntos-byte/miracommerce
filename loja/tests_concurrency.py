"""Testes opcionais de concorrência contra um banco real.

Execute com RUN_CONCURRENCY_TESTS=1 usando MySQL/MariaDB, nunca com SQLite em memória.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase

from .checkout import processar_finalizacao_compra
from .models import Categoria, MovimentacaoEstoque, Pedido, Produto


@skipUnless(os.environ.get('RUN_CONCURRENCY_TESTS') == '1', 'Teste de concorrência desativado por padrão.')
class ConcurrentCheckoutTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Concorrência')
        self.produto = Produto.objects.create(
            nome='Produto concorrente',
            categoria=self.categoria,
            preco=Decimal('10.00'),
            quantidade_estoque=1,
        )
        User = get_user_model()
        self.users = [
            User.objects.create_user(username=f'concorrente_{index}', password='SenhaForte#2026')
            for index in range(4)
        ]

    def checkout(self, user_id):
        close_old_connections()
        try:
            user = get_user_model().objects.get(pk=user_id)
            return processar_finalizacao_compra(user, {str(self.produto.pk): 1})
        except Exception as exc:  # A disputa esperada resulta em estoque insuficiente.
            return exc
        finally:
            close_old_connections()

    def test_apenas_um_checkout_consumira_ultima_unidade(self):
        with ThreadPoolExecutor(max_workers=len(self.users)) as executor:
            results = list(executor.map(self.checkout, [user.pk for user in self.users]))

        successes = [result for result in results if not isinstance(result, Exception)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(Pedido.objects.count(), 1)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 0)
        self.assertEqual(
            MovimentacaoEstoque.objects.filter(tipo=MovimentacaoEstoque.Tipo.VENDA).count(),
            1,
        )
