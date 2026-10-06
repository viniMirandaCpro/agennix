# Agennix

Sistema de gestao para barbearias (SaaS multi-tenant): agendamentos, lembretes
automaticos no WhatsApp, dashboards operacional e financeiro, API para
integradores e landing page de vendas.

> **Status:** estrutura do projeto criada. Nenhuma funcionalidade implementada
> ainda — os arquivos Python contem apenas um `TODO` indicando a historia de
> usuario que cada um atende.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Flask 3.1, Flask-RESTful, Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Banco | PostgreSQL 16 |
| Autenticacao | Flask-Login (sessao, para o painel) + API key por header (para integradores) |
| Agendador | APScheduler (lembretes de WhatsApp via Evolution API) |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS |
| Infra dev | Docker Compose |

## Decisoes de arquitetura

**Autenticacao hibrida.** O painel Next.js autentica por **cookie de sessao**
(Flask-Login). A API REST para integradores autentica por **chave no header
`X-API-Key`**, o que permite testar todos os endpoints no Postman sem depender
do navegador. Os dois caminhos vivem em `backend/app/auth/` e sao independentes.

**RBAC proprio.** O pacote Flask-RBAC esta abandonado, entao o controle de
acesso por perfil (Administrador, Atendente, Profissional, Cliente) e feito por
um decorator proprio em `backend/app/auth/rbac.py`.

**Multitenant por coluna.** Todo modelo de negocio carrega `tenant_id` via
`TenantMixin` (`backend/app/models/mixins.py`), e `backend/app/utils/tenant.py`
centraliza o filtro para que nenhuma consulta vaze dados de outra barbearia.

## Estrutura

```
agennix/
├── docker-compose.yml       # postgres + backend + frontend
├── backend/
│   ├── config.py            # Config por ambiente
│   ├── wsgi.py              # entrypoint do gunicorn
│   └── app/
│       ├── __init__.py      # application factory
│       ├── extensions.py    # db, migrate, login_manager, cors, api
│       ├── models/          # um arquivo por entidade
│       ├── resources/       # endpoints Flask-RESTful
│       ├── schemas/         # validacao de entrada / serializacao
│       ├── services/        # regra de negocio
│       ├── auth/            # sessao, api key e RBAC
│       ├── tasks/           # jobs do APScheduler
│       └── utils/           # erros, respostas, tenant, telefone
└── frontend/
    └── src/app/
        ├── (marketing)/     # landing page publica
        ├── (booking)/       # agendamento sem login
        ├── (auth)/          # login
        └── (dashboard)/     # painel autenticado
```

Os parenteses no frontend sao **route groups** do Next.js: nao aparecem na URL,
servem para dar um `layout.tsx` proprio a cada area (a landing page nao carrega
a sidebar do painel, por exemplo).

## Como rodar

```bash
# 1. Variaveis de ambiente
cp .env.example .env
cp backend/.env.example backend/.env

# 2. Subir tudo
docker compose up -d

# 3. Criar as migracoes (apos os modelos terem colunas)
docker compose exec backend flask db init
docker compose exec backend flask db migrate -m "estrutura inicial"
docker compose exec backend flask db upgrade
```

- Painel: http://localhost:3000
- API: http://localhost:5000

### Sem Docker (apenas backend)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
flask run --debug
```

Neste caso ajuste `DATABASE_URL` em `backend/.env` para apontar ao Postgres
local (`@localhost:5432` em vez de `@db:5432`).

## Proximo passo

Implementar os modelos em `backend/app/models/`, gerar a primeira migracao e
entregar a historia de **login**, que destrava todas as demais.
