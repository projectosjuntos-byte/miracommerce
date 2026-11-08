# 🚀 Guia de Hospedagem na Vercel — MiraComerce IA

Este projeto foi completamente preparado e otimizado para deploy serverless de alto desempenho na **Vercel**, mantendo 100% de compatibilidade com o seu ambiente de desenvolvimento local (XAMPP / MySQL).

---

## 📁 Estrutura de Arquivos Criada para a Vercel

| Arquivo | Finalidade |
| :--- | :--- |
| **[`api/index.py`](file:///c:/xampp/htdocs/loja/api/index.py)** | Ponto de entrada Serverless WSGI que atende todas as requisições HTTP na Vercel. |
| **[`vercel.json`](file:///c:/xampp/htdocs/loja/vercel.json)** | Configuração de roteamento Edge CDN (para `/static/` e `/media/`) e execução do runtime `@vercel/python`. |
| **[`build_files.sh`](file:///c:/xampp/htdocs/loja/build_files.sh)** | Script automático de build que instala os pacotes, coleta os arquivos estáticos (`collectstatic`) e prepara o projeto. |
| **[`.vercelignore`](file:///c:/xampp/htdocs/loja/.vercelignore)** | Exclui pastas pesadas (`.venv`, `node_modules`, `*.sqlite3`, caches) para manter o deploy leve e rápido. |
| **[`requirements.txt`](file:///c:/xampp/htdocs/loja/requirements.txt)** | Ajustado com `PyMySQL` e `dj-database-url` para evitar erros de compilação C no Linux da Vercel. |

---

## 🗄️ Importante: Banco de Dados na Vercel

O ambiente da Vercel é **Serverless** (funções efémeras que dormem após o uso e possuem sistema de ficheiros somente-leitura). Por esse motivo, **não é possível usar SQLite local para guardar dados persistentes na Vercel**.

O Django na MiraComerce IA foi configurado para reconhecer automaticamente a variável **`DATABASE_URL`**.

### Opções Gratuitas Recomendadas para Banco de Dados na Nuvem:
1. **[Neon.tech](https://neon.tech)** *(Recomendado - PostgreSQL Serverless Grátis)*:
   * Criação em 1 minuto. Copie a string de conexão fornecida.
   * Formato: `postgresql://usuario:senha@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require`
2. **[Supabase.com](https://supabase.com)** *(PostgreSQL Grátis)*:
   * Formato: `postgresql://postgres:senha@db.xyz.supabase.co:5432/postgres`
3. **[Railway.app](https://railway.app)** ou **[PlanetScale](https://planetscale.com)** *(MySQL Grátis / Trial)*:
   * Formato: `mysql://root:senha@monorail.proxy.rlwy.net:12345/railway`

---

## 🛠️ Passo a Passo para Hospedar na Vercel

### Passo 1: Subir o código para o GitHub
No terminal do seu computador (fora de qualquer ambiente virtual):
```bash
git init
git add .
git commit -m "feat: configuracao completa para deploy na Vercel"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

### Passo 2: Importar no painel da Vercel
1. Acesse [vercel.com](https://vercel.com) e faça login com a sua conta GitHub.
2. Clique em **"Add New..."** > **"Project"**.
3. Selecione o repositório do seu e-commerce e clique em **"Import"**.
4. Em **Framework Preset**, deixe **"Other"** (o arquivo `vercel.json` cuidará de tudo automaticamente).

### Passo 3: Configurar as Variáveis de Ambiente (Environment Variables)
No painel de configuração antes de clicar em Deploy, adicione as seguintes variáveis na seção **Environment Variables**:

| Variável | Valor Recomendado | Descrição |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Gere uma chave longa aleatória)* | Chave de segurança criptográfica do Django |
| `DEBUG` | `False` | Desativa o modo debug para produção |
| `DATABASE_URL` | `postgresql://...` ou `mysql://...` | Link do seu banco de dados na nuvem (Neon/Supabase/Railway) |
| `VERCEL` | `1` | Informa ao Django que está rodando na Vercel |

*(Opcional: se desejar envio de e-mails reais, configure `EMAIL_HOST_USER` e `EMAIL_HOST_PASSWORD`)*

### Passo 4: Fazer o Deploy
* Clique no botão azul **"Deploy"**.
* A Vercel executará o `build_files.sh`, instalará as dependências, coletará os arquivos estáticos e publicará o seu site em poucos segundos!
* O seu site receberá automaticamente uma URL com certificado SSL grátis (ex: `https://sua-loja.vercel.app`).
