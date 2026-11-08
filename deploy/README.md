# Deploy de produção

Os arquivos desta pasta são modelos reproduzíveis. Substitua o domínio,
credenciais e caminhos antes de ativar qualquer serviço.

## Docker Compose

1. Copie `.env.production.example` para `.env.production` e preencha todos os valores.
2. Gere uma `SECRET_KEY` longa e configure o domínio real em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.
3. Execute `docker compose --env-file deploy/.env.production -f deploy/docker-compose.prod.yml up -d --build`.
4. Execute `docker compose --env-file deploy/.env.production -f deploy/docker-compose.prod.yml exec web python manage.py migrate --noinput`.
5. O Compose inclui Nginx e publica apenas `127.0.0.1:8080`. Aponte o proxy TLS
   do host para essa porta; ele deve substituir `X-Real-IP`, `X-Forwarded-For` e
   `X-Forwarded-Proto`, tal como o modelo em `nginx/miracommerce.conf`.

## Gunicorn, Nginx e systemd

1. Instale o projeto em `/srv/miracommerce` e crie `/etc/miracommerce.env` a partir do exemplo.
2. Execute `python manage.py migrate --noinput` e `python manage.py collectstatic --noinput`.
3. Copie os três serviços systemd para `/etc/systemd/system/`.
4. Copie o arquivo Nginx para `/etc/nginx/sites-available/miracommerce.conf`, ajuste o domínio e ative o site.
5. Use TLS real, por exemplo via Certbot, antes de habilitar `SECURE_SSL_REDIRECT=True`.
6. Ative os serviços: `systemctl enable --now miracommerce-web miracommerce-worker miracommerce-beat`.

Redis usa AOF e volume persistente no Compose. O banco MySQL também usa volume
persistente. Em múltiplas instâncias web, troque o storage local de media por
um storage compartilhado compatível com o backend configurado.

## Pagamentos

O pagamento interno é exclusivamente uma simulação de desenvolvimento e fica
desativado no exemplo de produção. Antes de aceitar vendas reais, implemente o
provedor escolhido, um webhook autenticado e a confirmação que muda o pedido
de `pending_payment` para `paid`; somente essa confirmação deve baixar o
estoque e conceder o bónus.
