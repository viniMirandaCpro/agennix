# Agennix

Sistema de agendamento para estabelecimentos de servico por hora marcada —
barbearias, saloes, clinicas, estudios, consultorios. SaaS multi-tenant com
lembretes automaticos por SMS, dashboards operacional e financeiro, API
para integradores e landing page de vendas.

> **Status:** MVP implementado - login, cadastro de profissionais (com
> expediente) e servicos, agenda do painel, agendamento publico pelo link
> `/agendar/{slug}`, perfis de acesso (RBAC) com cadastro de usuarios e
> confirmacao/lembrete por SMS (Twilio). As demais historias (financeiro,
> pacotes, planos, API keys, landing page) seguem como `TODO` nos arquivos.

## Modelagem do banco

O desenho completo esta em **[docs/modelagem.md](docs/modelagem.md)**: diagrama
ER, dicionario de dados das 19 tabelas, constraints e a matriz que rastreia
cada criterio de aceitacao ate a tabela/coluna que o atende.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Flask 3.1, Flask-RESTful, Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Banco | PostgreSQL 16 |
| Autenticacao | Flask-Login (sessao, para o painel) + API key por header (para integradores) |
| Agendador | APScheduler (lembretes por SMS via Twilio) |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS |
| Infra dev | Docker Compose |

## Decisoes de arquitetura

**Autenticacao hibrida.** O painel Next.js autentica por **cookie de sessao**
(Flask-Login). A API REST para integradores autentica por **chave no header
`X-API-Key`**, o que permite testar todos os endpoints no Postman sem depender
do navegador. Os dois caminhos vivem em `backend/app/auth/` e sao independentes.

**RBAC proprio.** O pacote Flask-RBAC esta abandonado, entao o controle de
acesso por perfil e feito por um decorator proprio em
`backend/app/auth/rbac.py`. Sao tres perfis de login, guardados no enum
`users.role`: Administrador, Atendente e Profissional. O **cliente final nao e
um perfil de login** — ele agenda sem senha (tabela `clients`) e so cria conta
se quiser acompanhar o historico.

**Multitenant por coluna.** Um unico banco, um unico schema: todo modelo de
negocio carrega `tenant_id` via `TenantMixin` (`backend/app/models/mixins.py`),
e `backend/app/utils/tenant.py` centraliza o filtro para que nenhuma consulta
vaze dados de outro estabelecimento. A garantia final fica no banco, com FK
composta `(tenant_id, id)`.

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
docker compose up -d --build

# 3. Criar as tabelas e o estabelecimento de demonstracao
docker compose exec backend flask db upgrade
docker compose exec backend flask seed
```

- Painel: http://localhost:3000/login - senha `agennix123` para os tres perfis:

  | Login | Perfil | O que acessa |
  |---|---|---|
  | `admin@agennix.dev` | Administrador | Tudo, inclusive cadastros e usuarios (Configuracoes) |
  | `atendente@agennix.dev` | Atendente | Agenda completa |
  | `carlos@agennix.dev` | Profissional | So a propria agenda, sem editar |
- Link publico de agendamento: http://localhost:3000/agendar/demo
- API: http://localhost:5000/api

> **macOS:** a porta 5000 costuma estar ocupada pelo AirPlay Receiver. Nesse
> caso use `BACKEND_PORT=5001` no `.env` (o frontend do compose acompanha).
> Se a 5432 tambem estiver em uso, troque `POSTGRES_PORT`.

O `docker compose up` tambem sobe o servico `scheduler` (`flask scheduler`),
que a cada minuto cria os lembretes da janela e envia os SMS pendentes.

### SMS (Twilio)

A confirmacao sai quando o cliente agenda pelo link publico; o lembrete sai
`REMINDER_HOURS_BEFORE` horas (padrao 2) antes de qualquer agendamento. Sem
credenciais, as mensagens ficam em `notifications` com o erro
`Twilio não configurado` e viram `falhou` na 3a tentativa.

1. Crie uma conta de teste em twilio.com e pegue um numero de envio.
2. Em *Verified Caller IDs*, verifique o celular que vai receber os testes
   (a conta de teste so envia para numeros verificados).
3. Em *Messaging > Settings > Geo Permissions*, libere o Brasil.
4. Preencha `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` e,
   se quiser, `REMINDER_HOURS_BEFORE` em `backend/.env`.
5. `docker compose up -d scheduler` (recria o container com o `.env` novo;
   `restart` mantem as variaveis antigas)

A conta de teste do Twilio so envia os modelos prontos dele (`sms_appointment_reminders`
etc.) e recusa o texto do Agennix com "Trial accounts can only use predefined SMS
templates". Para os SMS de verdade, faca o upgrade da conta. Para conferir o que saiu:
`docker compose exec db psql -U agennix -c "select type,status,attempts,error_message from notifications"`.

### Testes

```bash
# backend - Postgres real (EXCLUDE/tstzrange nao existem no SQLite)
docker compose exec db createdb -U agennix agennix_test   # so na primeira vez
docker compose exec backend pytest

# frontend
cd frontend && npm test && npm run lint
```

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

Com agendamento, perfis e SMS de pe, a proxima historia e o dashboard
financeiro (5.6): ja pode usar `roles_required("administrador")`, mas antes
precisa dos modelos `payments` e `expenses` desenhados em `docs/modelagem.md`.
