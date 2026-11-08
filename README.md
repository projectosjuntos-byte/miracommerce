# MiraComerce IA

MiraComerce IA é uma loja virtual desenvolvida em Django para venda de produtos com foco em experiência de compra, gestão de catálogo, promoções e recomendações por IA.

O projeto inclui:
- vitrine com categorias e subcategorias
- carrinho de compras
- finalização de compra com validação de estoque
- bônus por compra
- painel administrativo
- recomendações baseadas em padrões de compra
- onboarding/guia para novos usuários
- cache para reduzir carga e melhorar tempo de resposta

## Stack principal

- Python 3.13
- Django 4.2+
- MySQL / MariaDB
- Bootstrap 5
- Django Redis
- Redis
- Celery

## Visão geral do projeto

A aplicação segue o padrão Django MVC (Model-View-Template), com um fluxo principal:

- usuários navegam pela vitrine em home
- acessam categorias e subcategorias
- adicionam produtos ao carrinho
- finalizam a compra com validação de estoque e cálculo de bônus
- o sistema registra vendas para alimentar recomendações futuras

## Estrutura de pastas

```text
loja/
├── admin.py
├── apps.py
├── checkout.py
├── estoque.py
├── auditoria.py
├── forms.py
├── models.py
├── promocoes.py
├── recomendacoes.py
├── relatorios.py
├── services.py
├── tests.py
├── urls.py
├── utils.py
├── views.py
├── migrations/
│   └── ...
├── templates/
│   └── loja/
│       ├── base.html
│       ├── index.html
│       ├── carrinho.html
│       ├── guia.html
│       ├── login.html
│       └── ...
└── static/
    └── ...

meu_ecommerce/
├── __init__.py
├── settings.py
├── urls.py
├── asgi.py
├── wsgi.py

static/
├── loja/
└── ...

## Arquitetura de domínio

As views usam a fachada de [loja/services.py](loja/services.py), que separa
catálogo, carrinho, pedidos, pagamentos, recomendações e relatórios. Os
módulos antigos continuam disponíveis apenas como compatibilidade, enquanto
novas regras devem ser adicionadas na camada de serviços ou no módulo de
domínio correspondente.

Produtos possuem SKU único. As recomendações e regras de associação usam
`produto_id`, evitando depender do nome do produto. Cada `Venda` armazena a
quantidade do item, em vez de repetir uma linha por unidade. Alterações de estoque são
registradas em `MovimentacaoEstoque`, e mudanças administrativas ficam em
`AuditoriaAdministrativa`. Pedidos também mantêm histórico de status.

templates/
└── loja/

media/
└── produtos/

loadtests/
├── locustfile.py
├── README.md
```

## Funcionalidades principais

### Vitrine e catálogo
- listagem de produtos por categoria e subcategoria
- busca por nome
- menu com categorias e subcategorias
- cards com nome, preço, promoções e botão de compra

### Carrinho e checkout
- adicionar, remover e editar itens
- cálculo de subtotal e total
- validação de estoque
- processamento transacional da compra
- cálculo de bônus por compra

### Promoções
- descontos automáticos por data de validade
- promoção manual no admin
- cálculo de preço promocional dinâmico

### Recomendações IA
- geração incremental de regras de coocorrência com base em compras anteriores
- sugestões para itens relacionados
- sugestões para carrinho
- cache para reduzir custo de processamento
- janela temporal, teto de transações e limite de itens por pedido configuráveis

### Administração
- gestão de produtos, categorias, subcategorias e usuários
- relatórios de vendas
- visualização de estoque baixo e produtos próximos da validade

### Onboarding
- guia de boas-vindas para novos usuários
- modal de introdução na home
- menu de primeiros passos

## Requisitos

Antes de rodar o projeto, certifique-se de ter instalado:

- Python 3.11+ (o projeto foi validado com 3.13)
- MySQL ou MariaDB
- Redis (opcional, para cache distribuído)
- pip
- virtualenv / venv

## Configuração do ambiente

1. Crie e ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

Se o projeto possuir um requirements.txt no futuro, use:

```bash
pip install -r requirements.txt
```

## Variáveis de ambiente

O projeto lê variáveis de ambiente para configuração de banco, cache e produção.

Exemplo:

```bash
export DEBUG=True
export DB_NAME=ecommerce_inteligente
export DB_USER=root
export DB_PASSWORD=
export DB_HOST=localhost
export DB_PORT=3306
export CACHE_TIMEOUT=900
export RECOMENDACAO_CACHE_TIMEOUT=3600
export CATALOG_PAGE_SIZE=24
export RECOMMENDATION_LOOKBACK_DAYS=365
export RECOMMENDATION_MAX_TRANSACTIONS=20000
export RECOMMENDATION_MAX_ITEMS_PER_TRANSACTION=50
export RECOMMENDATION_MIN_SUPPORT=0.01
export RECOMMENDATION_MIN_LIFT=1.0
export RECOMMENDATION_MAX_RULES=500
export USE_REDIS_CACHE=False
export REDIS_URL=redis://127.0.0.1:6379/1
export CELERY_BROKER_URL=redis://127.0.0.1:6379/2
export CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2
export CELERY_TASK_ALWAYS_EAGER=True
```

No Windows PowerShell:

```powershell
$env:DEBUG="True"
$env:DB_NAME="ecommerce_inteligente"
$env:DB_USER="root"
$env:DB_PASSWORD=""
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:CACHE_TIMEOUT="900"
$env:RECOMENDACAO_CACHE_TIMEOUT="3600"
$env:CATALOG_PAGE_SIZE="24"
$env:RECOMMENDATION_LOOKBACK_DAYS="365"
$env:RECOMMENDATION_MAX_TRANSACTIONS="20000"
$env:RECOMMENDATION_MAX_ITEMS_PER_TRANSACTION="50"
$env:RECOMMENDATION_MIN_SUPPORT="0.01"
$env:RECOMMENDATION_MIN_LIFT="1.0"
$env:RECOMMENDATION_MAX_RULES="500"
$env:USE_REDIS_CACHE="False"
$env:REDIS_URL="redis://127.0.0.1:6379/1"
$env:CELERY_BROKER_URL="redis://127.0.0.1:6379/2"
$env:CELERY_RESULT_BACKEND="redis://127.0.0.1:6379/2"
$env:CELERY_TASK_ALWAYS_EAGER="True"
```

## Banco de dados

Configure o banco no arquivo:

- [meu_ecommerce/settings.py](meu_ecommerce/settings.py)

### Criação das tabelas

```bash
python manage.py migrate
```

O arquivo migration_mysql8.sql é apenas um snapshot histórico e está
desatualizado. Não o execute em produção: ele contém comandos destrutivos
(DROP TABLE) e não representa as migrações atuais. A fonte oficial do schema
são as migrações Django.

### Criar superusuário

```bash
python manage.py createsuperuser
```

## Execução local

```bash
python manage.py runserver 127.0.0.1:8000
```

Acesse:

- http://127.0.0.1:8000/
- painel administrativo em http://127.0.0.1:8000/admin/

## Cache

O sistema já possui cache configurado para reduzir tempo de resposta em páginas frequentes.

### Cache local
O padrão atual usa:
- `LocMemCache`

### Cache Redis
Para ativar cache Redis em produção ou em ambiente de teste:

```bash
export USE_REDIS_CACHE=True
export REDIS_URL=redis://127.0.0.1:6379/1
```

Depois reinicie o servidor Django.

## Testes

Para executar os testes do projeto:

```bash
python manage.py test
```

Para reproduzir a validação do CI:

```bash
pip install -r requirements-dev.txt
python manage.py check
python manage.py migrate --noinput
python manage.py makemigrations --check
coverage run manage.py test --noinput
coverage report --fail-under=50
ruff check loja meu_ecommerce manage.py
bandit -q -r loja meu_ecommerce -x loja/migrations,loja/tests.py
```

Também há foco em testes de fluxo de negócio importantes, como:
- promoção automática
- compra com preço promocional
- rollback do checkout em falhas de estoque e persistência
- cadastro, sessão e recuperação de senha
- validação de upload de imagens
- execução das tarefas assíncronas
- recomendação por categoria
- paginação do catálogo e regras de recomendação por pedidos e histórico legado
- exibição de subcategorias na vitrine
- filtro por subcategoria

## Tarefas assíncronas

Em produção, execute um worker e o agendador Celery com Redis:

    celery -A meu_ecommerce worker -l INFO
    celery -A meu_ecommerce beat -l INFO

No Windows, o worker pode ser iniciado com --pool=solo. As promoções são atualizadas
a cada 15 minutos e as regras de recomendação a cada hora. Em desenvolvimento,
CELERY_TASK_ALWAYS_EAGER=True executa as tarefas no próprio processo.

## Produção

Os modelos de Gunicorn, Nginx, systemd, Docker Compose, Redis persistente,
SMTP e storage ficam em [deploy/](deploy/). Preencha
[deploy/.env.production.example](deploy/.env.production.example), execute as
migrações e configure TLS antes de ativar o redirecionamento HTTPS.

## Load testing

A pasta [loadtests/](loadtests/) contém scripts para testes de carga, com foco em usuários autenticados e interações reais.

Exemplo de execução com Locust:

```bash
pip install locust
locust -f loadtests/locustfile.py
```

## Observações importantes

### Banco
O Django exige uma versão compatível do MariaDB/MySQL. O ambiente local atual apresentou incompatibilidade com MariaDB 10.4.x; a versão mínima recomendada é MariaDB 10.11+.

### Segurança
O modo de produção exige SECRET_KEY, DB_PASSWORD, credenciais SMTP e hosts
configurados. Também ativa HTTPS, HSTS, cookies seguros, proteção CSRF,
X-Frame-Options, nosniff e política de referenciador. Use .env.example como
modelo e nunca versiona o .env real.

Uploads de produto aceitam apenas JPEG, PNG e WEBP válidos, até 5 MB e 4000x4000
pixels, sendo armazenados com nome aleatório.

Login e recuperação de senha possuem limitação de tentativas configurável.
O frete também é configurável por FRETE_GRATIS_MINIMO e FRETE_PADRAO.

Os endpoints /health/live/ e /health/ready/ podem ser usados pelo proxy ou
orquestrador. O workflow em .github/workflows/ci.yml executa checks, migrações,
testes e validação de dependências.

### Acessibilidade e frontend
Os assets do frontend usados pela loja são locais: Bootstrap, ícones e scripts
de carrinho/tour. Os botões de ícone possuem nomes acessíveis, existe link para
salto de conteúdo, estados de foco visíveis e suporte a `prefers-reduced-motion`.
Imagens de produto possuem dimensões, `alt`, carregamento lazy e thumbnail JPEG.
Para imagens antigas, execute `python manage.py gerar_thumbnails_produtos`.

### Relatórios
Gestores autenticados podem acessar `/relatorios/vendas/`, filtrar por data e
exportar CSV, Excel compatível (SpreadsheetML) ou PDF. Os filtros e a página
atual são preservados nos links de paginação e exportação.

### Privacidade
Em `/privacidade/`, o utilizador autenticado pode baixar os dados em JSON ou
solicitar anonimização. A anonimização remove os dados pessoais e preserva o
histórico financeiro sem identificação. O comando
`python manage.py anonimizar_usuarios_inativos --dias 1825` pode ser usado em
rotinas operacionais; o Celery também agenda essa verificação diariamente.

### Produção
Para produção, aconselha-se:
- Redis em produção
- cache de sessão e de recomendação
- banco em versão compatível
- uso de servidor WSGI/ASGI com Gunicorn/uWSGI
- reverse proxy com Nginx
- monitoramento de erros e latência
- ambiente com variáveis seguras e secrets externas

## Roadmap recomendado

- migrar cache local para Redis em produção
- adicionar gateway de pagamento com idempotência e webhooks assinados
- monitorar falhas e duração dos workers Celery
- separar dashboard e relatórios em módulos específicos
- testar carga real com usuários autenticados
- revisar índices do banco e consultas frequentes
- melhorar observabilidade e métricas de performance

## Contribuição

Este projeto foi desenvolvido como solução de loja virtual com IA aplicada ao e-commerce.

Contribuições e melhorias são bem-vindas, especialmente em:
- desempenho
- arquitetura
- testes automatizados
- UX
- segurança

## Licença

Este projeto foi criado para fins acadêmicos e de demonstração de desenvolvimento de software, sendo adequado para uso como base de estudo e extensão.

## Contato

Projeto desenvolvido em ambiente local para estudo e evolução de um sistema de e-commerce com inteligência artificial aplicada.
