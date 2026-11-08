import os
import re
from typing import List

from locust import HttpUser, between, task

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')
USERNAME = os.environ.get('LOGIN_USER', 'cliente1')
PASSWORD = os.environ.get('LOGIN_PASSWORD', 'senha123')


class AuthenticatedStoreUser(HttpUser):
    wait_time = between(1, 3)
    host = BASE_URL
    product_ids: List[int] = []

    def on_start(self):
        self.login()
        self.product_ids = self.discover_products()

    def login(self):
        response = self.client.get('/login/', name='GET /login')
        csrf_token = self._extract_csrf(response.text)
        payload = {
            'username': USERNAME,
            'password': PASSWORD,
            'csrfmiddlewaretoken': csrf_token,
        }
        headers = {'X-CSRFToken': csrf_token}
        self.client.post('/login/', data=payload, headers=headers, name='POST /login')

    def _extract_csrf(self, html: str) -> str:
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)', html)
        if match:
            return match.group(1)
        return ''

    def discover_products(self) -> List[int]:
        response = self.client.get('/', name='GET /')
        ids = re.findall(r'/carrinho/add/(\d+)/', response.text)
        return [int(item) for item in ids[:20]]

    @task(3)
    def open_home(self):
        self.client.get('/', name='GET /')

    @task(2)
    def browse_category(self):
        self.client.get('/categoria/1/', name='GET /categoria/:id')

    @task(2)
    def open_cart(self):
        self.client.get('/carrinho/', name='GET /carrinho')

    @task(4)
    def add_product_to_cart(self):
        if not self.product_ids:
            return
        product_id = self.product_ids[0]
        cart_page = self.client.get('/carrinho/', name='GET /carrinho add')
        csrf_token = self._extract_csrf(cart_page.text)
        if not csrf_token:
            return
        self.client.post(
            f'/carrinho/add/{product_id}/',
            data={'csrfmiddlewaretoken': csrf_token},
            headers={'X-CSRFToken': csrf_token},
            name='POST /carrinho/add/:id',
        )

    @task(1)
    def checkout(self):
        cart_page = self.client.get('/carrinho/', name='GET /carrinho checkout')
        csrf_token = self._extract_csrf(cart_page.text)
        if not csrf_token:
            return
        self.client.post(
            '/finalizar-compra/',
            data={'csrfmiddlewaretoken': csrf_token},
            headers={'X-CSRFToken': csrf_token},
            name='POST /finalizar-compra',
        )

    @task(2)
    def visit_support_pages(self):
        self.client.get('/sobre/', name='GET /sobre')
        self.client.get('/ajuda/', name='GET /ajuda')
