# Testes de carga para usuários autenticados

Este diretório contém um cenário realista para medir a latência da vitrine, do carrinho e do checkout com usuários autenticados.

## Como executar

1. Ative o ambiente do projeto:

   ```powershell
   cd C:\xampp\htdocs\loja
   .\.venv-1\Scripts\Activate.ps1
   ```

2. Instale o Locust:

   ```powershell
   python -m pip install locust
   ```

3. Inicie o servidor Django:

   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```

4. Rode o teste de carga:

   ```powershell
   locust -f loadtests/locustfile.py --host=http://localhost:8000
   ```

5. Abra no navegador:

   - http://localhost:8089

6. Configure:

   - Number of users: 20, 50, 100, 200
   - Spawn rate: 5 a 20 por segundo
   - Duration: 3 a 10 minutos

## Rotas principais monitoradas

- GET /
- GET /carrinho/
- GET /sobre/
- GET /ajuda/
- POST /carrinho/add/:id/
- POST /finalizar-compra/

## Métricas de latência esperadas

Para uma aplicação em carga moderada, os alvos práticos são:

- p95 da home: até 800 ms
- p95 do carrinho: até 800 ms
- p95 do checkout: até 1500 ms
- erro de requisição: menor que 1%

## Cenários recomendados

### Cenário A — carga leve

- 20 usuários simultâneos
- 3 minutos
- foco em navegação e autenticação

### Cenário B — carga média

- 50 usuários simultâneos
- 5 minutos
- foco em carrinho e checkout

### Cenário C — carga alta

- 100 a 200 usuários simultâneos
- 8 a 10 minutos
- foco em saturação de banco, cache e concorrência de estoque

## Tuning de banco e cache para alta demanda

### MySQL / InnoDB

Adicionar configurações como estas no arquivo my.cnf ou no serviço do banco:

```ini
[mysqld]
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_thread_concurrency = 0
max_connections = 300
query_cache_type = 0
sql_mode = STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION
``` 

### Cache recomendado

- Redis para cache de sessão e categorias
- cache de recomendações por 5 a 15 minutos
- cache de menu e catálogo por 5 minutos

Exemplo de settings:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 300,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
```

### Estratégia operacional

- evitar cálculo de IA em cada request
- gerar recomendações em background
- usar fila para relatórios e exportação de PDF
- gerar alertas de estoque em background
- usar logging e métricas por rota

## Medição de latência por rota

Além do dashboard do Locust, vale testar manualmente com:

```powershell
curl -w "time_namelookup: %{time_namelookup}\n time_connect: %{time_connect}\n time_starttransfer: %{time_starttransfer}\n time_total: %{time_total}\n" -o NUL http://localhost:8000/
```

Também vale usar ferramentas como:

- k6
- ApacheBench
- JMeter

## Observação

Para produção real, gere regras de associação e relatórios em background e não no request principal. Isso reduz o risco de picos de CPU e gargalos na base de dados.
