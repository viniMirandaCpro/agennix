# Lembretes e confirmacao por SMS - Plano de implementacao

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enviar SMS de confirmacao no agendamento publico e lembrete N horas antes de cada agendamento, via Twilio, sem nunca enviar em dobro.

**Architecture:** O agendamento publico grava uma `Notification` pendente na mesma transacao. Um processo proprio (`flask scheduler`, APScheduler) roda `run_once` a cada minuto: cria os lembretes que entraram na janela e envia todas as pendentes pelo Twilio, gravando resultado e erro em cada linha.

**Tech Stack:** Flask 3.1, Flask-SQLAlchemy, Alembic, PostgreSQL 16, APScheduler 3.11.3, requests 2.34.2, pytest. Frontend Next.js (so rotulos).

**Spec:** `docs/superpowers/specs/2026-11-23-lembretes-sms-design.md`

## Global Constraints

- Canal `sms`; valores de `notifications`: `type` em (`confirmacao`, `lembrete`), `channel` em (`sms`, `email`), `status` em (`pendente`, `enviada`, `falhou`).
- `UNIQUE (appointment_id, type)` com nome `notifications_unique_per_appointment`.
- Texto do SMS sem acento; data `dd/mm` e hora `HH:MM` no fuso do estabelecimento (`tenant.timezone`); primeiro nome do cliente.
- Confirmacao: `{Estab}: Ola {Nome}, seu horario de {Servico} com {Prof} esta confirmado para {dd/mm} as {HH:MM}.`
- Lembrete: `{Estab}: Ola {Nome}, lembrete: {Servico} com {Prof} em {dd/mm} as {HH:MM}.`
- `MAX_ATTEMPTS = 3`; timeout HTTP 10 s; `REMINDER_HOURS_BEFORE` padrao 2.
- Config: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `REMINDER_HOURS_BEFORE`.
- Sem dependencia nova: Twilio por `requests.post`, nao pelo SDK.
- A coluna `clients.whatsapp` e `normalize_whatsapp` mantem o nome.
- Testes nunca chamam a rede: `requests.post` ou `send_sms` sempre substituidos por fake.
- Commits em portugues, prefixo `backend:`, `frontend:` ou `docs:`, sem linha `Co-Authored-By`.
- Testes do backend: `docker compose exec backend pytest` (Postgres real).

## Review Focus

- Agendamento perto da meia-noite: 02:30 UTC sai como `30/11 as 23:30` em Sao Paulo, nao `01/12` (Task 2, `test_message_uses_tenant_timezone`).
- Twilio fora do ar ou erro de rede numa mensagem nao impede as outras da rodada (Task 4, `test_one_failure_does_not_block_others`).
- Cliente cadastrado so com e-mail nao gera lembrete nem quebra o job (Task 4, `test_no_reminder_for_client_without_phone`).
- Agendamento remarcado depois do lembrete enviado nao recebe segundo lembrete e o job nao levanta `IntegrityError` (Task 4, `test_moved_after_reminder_is_not_reminded_again`).
- Job parado e religado depois do inicio do atendimento nao manda lembrete atrasado (Task 4, `test_no_reminder_for_started_appointment`).

---

### Task 0: Branch e documentos

- [ ] **Step 1:** `git switch -c lembretes-sms`
- [ ] **Step 2: Commit dos documentos ja escritos**

```bash
git add docs/modelagem.md docs/superpowers/specs/2026-11-23-lembretes-sms-design.md docs/superpowers/plans/2026-11-23-lembretes-sms.md
git commit -m "docs: historia 5.3 passa de WhatsApp para SMS (Twilio), design e plano"
```

---

### Task 1: Modelo `Notification` e migracao

**Files:**
- Modify: `backend/app/models/notification.py` (hoje so docstring)
- Modify: `backend/app/models/__init__.py` (import + docstring "7 tabelas" vira 8)
- Create: `backend/migrations/versions/<rev>_notificacoes_sms.py` (autogerada)
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Produces: `app.models.Notification` com colunas `id` (BigInteger PK), `tenant_id` (TenantMixin), `appointment_id` (FK `appointments.id`, not null), `type` String(20), `channel` String(20) default `"sms"`, `destination` String(180), `status` String(20) default `"pendente"`, `scheduled_for` DateTime(tz) not null, `sent_at` DateTime(tz), `provider_message_id` String(120), `error_message` Text, `attempts` Integer not null default 0, `created_at`/`updated_at` (TimestampMixin); `appointment = db.relationship("Appointment")`. CHECKs `ck_notifications_type`, `ck_notifications_channel`, `ck_notifications_status` no padrao de `Appointment`; indice `ix_notifications_status_scheduled` em `(status, scheduled_for)`.

- [ ] **Step 1: Criar `backend/tests/test_notifications.py` com helpers e o teste do UNIQUE**

Helpers usados por todas as tasks seguintes:

```python
NOW = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)

@pytest.fixture
def customer(tenant):  # Client "Maria", whatsapp "+5511987654321"

def make_appt(tenant, professional, service, customer, starts_at, *, created_at=None, status="confirmado"):
    # Appointment direto no banco: ends_at = starts_at + 30 min, price_charged = service.price,
    # created_at = created_at or starts_at - timedelta(days=1); commit e retorna

def notify(appt, type="confirmacao", **kw):
    # Notification(tenant_id=appt.tenant_id, appointment=appt, type=type, channel="sms",
    #   destination=appt.client.whatsapp, scheduled_for=kw.pop("scheduled_for", NOW), **kw); add + commit; retorna
```

```python
def test_notification_is_unique_per_appointment_and_type(tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    notify(appt, "lembrete")
    with pytest.raises(IntegrityError):
        notify(appt, "lembrete")
    db.session.rollback()

def test_channel_rejects_whatsapp(tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    with pytest.raises(IntegrityError):
        notify(appt, channel="whatsapp")
    db.session.rollback()
```

- [ ] **Step 2:** `docker compose exec backend pytest tests/test_notifications.py -v`. Esperado: FAIL (`ImportError: cannot import name 'Notification'`).
- [ ] **Step 3: Implementar `Notification` em `backend/app/models/notification.py`** conforme Interfaces; docstring sem o TODO, citando a secao 3.19 e 4.6 da modelagem. Exportar em `app/models/__init__.py`.
- [ ] **Step 4:** `docker compose exec backend pytest tests/test_notifications.py -v`. Esperado: 2 passed.
- [ ] **Step 5: Gerar e revisar a migracao**

```bash
docker compose exec backend flask db migrate -m "notificacoes sms"
```

Abrir o arquivo gerado: deve conter so `create_table('notifications', ...)` com os 3 CHECKs, o UNIQUE, o indice e o indice de `tenant_id`, e o `drop_table` no downgrade. Apagar qualquer outra operacao que o autogenerate tenha detectado (ex.: constraint EXCLUDE). Renomear o arquivo para `<rev>_notificacoes_sms.py`.

- [ ] **Step 6:** `docker compose exec backend flask db upgrade` e depois `docker compose exec backend flask db downgrade && docker compose exec backend flask db upgrade`. Esperado: sem erro nas tres.
- [ ] **Step 7:** `docker compose exec backend pytest`. Esperado: toda a suite passa.
- [ ] **Step 8: Commit**

```bash
git add backend/app/models backend/migrations/versions backend/tests/test_notifications.py
git commit -m "backend: tabela notifications para confirmacao e lembrete por SMS"
```

---

### Task 2: Envio pelo Twilio e texto da mensagem

**Files:**
- Create: `backend/app/services/sms_service.py`
- Delete: `backend/app/services/whatsapp_service.py`
- Modify: `backend/config.py` (classe `Config`)
- Modify: `backend/.env.example` (bloco Evolution vira bloco Twilio)
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Consumes: `Notification` (Task 1).
- Produces:
  - `send_sms(to: str, body: str) -> str`: retorna o `sid` do Twilio. Le `current_app.config`. Sem `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` ou `TWILIO_FROM_NUMBER`: `RuntimeError("Twilio não configurado")`. POST em `https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json`, `auth=(SID, TOKEN)`, `data={"From": FROM, "To": to, "Body": body}`, `timeout=10`. Se `not r.ok`: `RuntimeError(r.json().get("message", r.text))`.
  - `message_for(notification: Notification) -> str`: texto da Global Constraints, sem acento (`unicodedata.normalize("NFKD", ...)` + `encode("ascii", "ignore")`), estabelecimento via `db.session.get(Tenant, notification.tenant_id)`.
  - `Config.TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (str, padrao `""`), `REMINDER_HOURS_BEFORE` (`int`, padrao 2).

- [ ] **Step 1: Escrever os testes**

Fake de `requests.post`: objeto com `ok`, `text` e `json()`, que grava `(url, kwargs)` numa lista. Substituir com `monkeypatch.setattr("app.services.sms_service.requests.post", fake)`. Configurar com `app.config.update(TWILIO_ACCOUNT_SID="AC1", TWILIO_AUTH_TOKEN="tok", TWILIO_FROM_NUMBER="+15550001111")`.

```python
def test_send_sms_posts_to_twilio(app, monkeypatch):
    # fake responde ok=True, json={"sid": "SM123"}
    assert send_sms("+5511987654321", "oi") == "SM123"
    url, kw = calls[0]
    assert url == "https://api.twilio.com/2010-04-01/Accounts/AC1/Messages.json"
    assert kw["auth"] == ("AC1", "tok")
    assert kw["data"] == {"From": "+15550001111", "To": "+5511987654321", "Body": "oi"}
    assert kw["timeout"] == 10

def test_send_sms_raises_twilio_error(app, monkeypatch):
    # fake responde ok=False, json={"message": "The number is unverified"}
    with pytest.raises(RuntimeError, match="unverified"):
        send_sms("+5511987654321", "oi")

def test_send_sms_without_credentials(app):
    app.config.update(TWILIO_ACCOUNT_SID="")
    with pytest.raises(RuntimeError, match="Twilio não configurado"):
        send_sms("+5511987654321", "oi")

def test_message_has_five_fields_without_accents(tenant, professional, service, customer):
    tenant.name, professional.name, customer.name = "Barbearia São Jorge", "João", "Ana Lúcia"
    appt = make_appt(tenant, professional, service, customer, datetime(2026, 11, 30, 13, 0, tzinfo=timezone.utc))
    assert message_for(notify(appt, "confirmacao")) == (
        "Barbearia Sao Jorge: Ola Ana, seu horario de Corte com Joao esta confirmado para 30/11 as 10:00."
    )
    assert message_for(notify(appt, "lembrete")) == (
        "Barbearia Sao Jorge: Ola Ana, lembrete: Corte com Joao em 30/11 as 10:00."
    )

def test_message_uses_tenant_timezone(tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, datetime(2026, 12, 1, 2, 30, tzinfo=timezone.utc))
    assert message_for(notify(appt, "lembrete")).endswith("em 30/11 as 23:30.")
```

- [ ] **Step 2:** `docker compose exec backend pytest tests/test_notifications.py -v`. Esperado: os 5 novos falham com `ModuleNotFoundError: app.services.sms_service`.
- [ ] **Step 3: Implementar `send_sms` e `message_for`** em `backend/app/services/sms_service.py`; apagar `whatsapp_service.py`; adicionar as 4 chaves em `Config`. Em `TestConfig`, fixar `REMINDER_HOURS_BEFORE = 2` e as tres `TWILIO_*` como `""`, para os testes nao dependerem do `backend/.env` nem usarem credencial real.
- [ ] **Step 4: `backend/.env.example`**: trocar o bloco `# --- Evolution API ...` (3 linhas) por:

```
# --- Twilio (SMS de confirmacao e lembrete) ---
# Conta de teste: so envia para numeros verificados no console.
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

- [ ] **Step 5:** `docker compose exec backend pytest tests/test_notifications.py -v`. Esperado: 7 passed.
- [ ] **Step 6: Commit**

```bash
git add backend/app/services backend/config.py backend/.env.example backend/tests/test_notifications.py
git commit -m "backend: envio de SMS pelo Twilio e texto da confirmacao e do lembrete"
```

---

### Task 3: Confirmacao no agendamento publico

**Files:**
- Modify: `backend/app/services/appointment_service.py:77-95` (`create_appointment`)
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Consumes: `Notification` (Task 1).
- Produces: todo agendamento com `source == "publico"` nasce com uma `Notification(type="confirmacao", channel="sms", status="pendente", destination=client.whatsapp, scheduled_for=datetime.now(timezone.utc))`, adicionada antes do `_commit()` (mesma transacao; um 409 de choque de horario nao deixa notificacao orfa).

- [ ] **Step 1: Escrever os testes** (importar `public_book` de `tests.test_public_booking` e `book` de `tests.test_appointments`)

```python
def test_public_booking_queues_confirmation(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    n = Notification.query.one()
    assert (n.type, n.channel, n.status, n.destination, n.attempts) == ("confirmacao", "sms", "pendente", "+5511987654321", 0)

def test_panel_booking_has_no_confirmation(auth_client, professional, service, customer):
    assert book(auth_client, professional, service, customer).status_code == 201
    assert Notification.query.count() == 0

def test_conflicting_public_booking_leaves_no_notification(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    assert public_book(client, professional, service, whatsapp="11912345678").status_code == 409
    assert Notification.query.count() == 1
```

- [ ] **Step 2:** `docker compose exec backend pytest tests/test_notifications.py -v`. Esperado: `test_public_booking_queues_confirmation` falha (`NoResultFound`).
- [ ] **Step 3: Implementar** a criacao da confirmacao em `create_appointment`.
- [ ] **Step 4:** `docker compose exec backend pytest`. Esperado: toda a suite passa.
- [ ] **Step 5: Commit**

```bash
git add backend/app/services/appointment_service.py backend/tests/test_notifications.py
git commit -m "backend: agendamento publico gera confirmacao por SMS (historia 5.12)"
```

---

### Task 4: Job de lembretes e envio

**Files:**
- Modify: `backend/app/tasks/reminders.py` (hoje so docstring)
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Consumes: `Notification` (Task 1); `send_sms`, `message_for` (Task 2), importados com `from app.services.sms_service import message_for, send_sms`.
- Produces: `run_once(now: datetime | None = None) -> None` (padrao `datetime.now(timezone.utc)`), que chama `queue_reminders(now)` e depois `send_pending(now)`; `MAX_ATTEMPTS = 3`. Janela `N = timedelta(hours=current_app.config["REMINDER_HOURS_BEFORE"])`.
  - `queue_reminders(now) -> None`: insere `Notification(type="lembrete", channel="sms", destination=client.whatsapp, scheduled_for=starts_at - N)` para agendamentos com status em (`pendente`, `confirmado`), `now < starts_at <= now + N`, `created_at <= starts_at - N`, `Client.whatsapp` nao nulo e sem lembrete existente; um commit.
  - `send_pending(now) -> None`: busca uma vez as `pendente` com `scheduled_for <= now` e trata cada uma: agendamento `cancelado` vira `falhou` com `error_message="Agendamento cancelado"`; senao `send_sms(n.destination, message_for(n))`. Sucesso: `enviada`, `sent_at=now`, `provider_message_id=sid`. Qualquer `Exception`: `attempts += 1`, `error_message=str(e)`, `falhou` se `attempts >= MAX_ATTEMPTS`. Em sucesso tambem `attempts += 1`. Commit depois de cada notificacao.
  - Comentario `ponytail:` no `send_pending`: sem trava de linha porque o agendador e um processo so; com mais de um, buscar com `FOR UPDATE SKIP LOCKED` e commit no fim do lote.

- [ ] **Step 1: Escrever os testes**

Fixture `sent`: `monkeypatch.setattr("app.tasks.reminders.send_sms", fake)`, em que `fake(to, body)` grava `(to, body)` numa lista e retorna `f"SM{len(lista)}"`. Com `REMINDER_HOURS_BEFORE = 2`, `NOW` da Task 1.

```python
def test_reminder_is_queued_and_sent_once(sent, tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    run_once(NOW); run_once(NOW)
    assert len(sent) == 1 and sent[0][0] == "+5511987654321" and "lembrete" in sent[0][1]
    n = Notification.query.one()
    assert (n.type, n.status, n.provider_message_id, n.attempts) == ("lembrete", "enviada", "SM1", 1)
    assert n.scheduled_for == appt.starts_at - timedelta(hours=2) and n.sent_at == NOW

def test_no_reminder_outside_window(...):           # starts_at = NOW + 3h -> sent == [], count 0
def test_no_reminder_when_booked_inside_window(...): # starts_at = NOW + 1h, created_at = NOW - 30 min -> nada
def test_no_reminder_for_cancelled(...):            # status="cancelado" -> nada
def test_no_reminder_for_started_appointment(...):  # starts_at = NOW - 10 min -> nada
def test_no_reminder_for_client_without_phone(...): # Client(whatsapp=None, email="ana@x.dev") -> nada, sem erro

def test_confirmation_is_sent_by_job(sent, client, professional, service):
    public_book(client, professional, service)
    run_once()
    assert len(sent) == 1 and "confirmado" in sent[0][1]
    assert Notification.query.one().status == "enviada"

def test_cancelled_before_confirmation_is_not_sent(sent, client, professional, service):
    public_book(client, professional, service)
    Appointment.query.one().status = "cancelado"; db.session.commit()
    run_once()
    n = Notification.query.one()
    assert sent == [] and (n.status, n.error_message) == ("falhou", "Agendamento cancelado")

def test_failure_retries_then_gives_up(monkeypatch, tenant, professional, service, customer):
    # send_sms fake levanta RuntimeError("boom")
    make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    run_once(NOW)
    n = Notification.query.one()
    assert (n.status, n.attempts, n.error_message) == ("pendente", 1, "boom")
    run_once(NOW); run_once(NOW)
    assert (n.status, n.attempts) == ("falhou", 3)

def test_one_failure_does_not_block_others(monkeypatch, tenant, professional, service, customer):
    # dois clientes em horarios diferentes; fake levanta ConnectionError so para o primeiro numero
    # -> o segundo lembrete termina "enviada", o primeiro "pendente" com attempts 1

def test_moved_after_reminder_is_not_reminded_again(sent, tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    run_once(NOW)
    appt.starts_at = NOW + timedelta(hours=1, minutes=30)
    appt.ends_at = appt.starts_at + timedelta(minutes=30); db.session.commit()
    run_once(NOW)
    assert len(sent) == 1
```

- [ ] **Step 2:** `docker compose exec backend pytest tests/test_notifications.py -v`. Esperado: os 11 novos falham (`ImportError: cannot import name 'run_once'`).
- [ ] **Step 3: Implementar** `queue_reminders`, `send_pending` e `run_once` em `backend/app/tasks/reminders.py`, com docstring sem TODO.
- [ ] **Step 4:** `docker compose exec backend pytest`. Esperado: toda a suite passa.
- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/reminders.py backend/tests/test_notifications.py
git commit -m "backend: job que cria lembretes na janela e envia SMS pendentes (historia 5.3)"
```

---

### Task 5: Comando `flask scheduler` e servico no docker-compose

**Files:**
- Modify: `backend/app/tasks/__init__.py` (hoje so docstring)
- Modify: `backend/app/__init__.py` (registrar o comando, como `seed_command`)
- Modify: `backend/requirements.txt` (fixar `APScheduler==3.11.3`, `requests==2.34.2`; comentario da secao vira `(SMS / Twilio)`)
- Modify: `docker-compose.yml` (remover bloco comentado da Evolution e o volume `evolution_instances`; adicionar servico `scheduler`)

**Interfaces:**
- Consumes: `run_once` (Task 4).
- Produces: `scheduler_command`, comando click `"scheduler"` com `@with_appcontext`: `BlockingScheduler()` com `add_job(run_once, "interval", minutes=1, max_instances=1, coalesce=True, next_run_time=datetime.now(timezone.utc))`, depois `start()`. O job roda dentro de `current_app.app_context()` (capturar `current_app._get_current_object()` antes do `start()`).

- [ ] **Step 1: Escrever o teste** (em `test_notifications.py`)

```python
def test_scheduler_command_is_registered(app):
    assert "scheduler" in app.cli.commands
```

- [ ] **Step 2:** rodar; esperado FAIL.
- [ ] **Step 3: Implementar** o comando e registrar em `create_app`.
- [ ] **Step 4: Servico no `docker-compose.yml`**, depois de `backend`:

```yaml
  scheduler:
    build: ./backend
    container_name: agennix-scheduler
    restart: unless-stopped
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - /app/venv
    depends_on:
      db:
        condition: service_healthy
    command: flask scheduler
```

- [ ] **Step 5:** `docker compose exec backend pytest`. Esperado: toda a suite passa.
- [ ] **Step 6: Verificacao manual**

```bash
docker compose up -d --build scheduler
docker compose logs scheduler --tail 20
```

Esperado: log do APScheduler com `Added job "run_once"` e execucoes a cada minuto sem traceback. Fazer um agendamento em `http://localhost:3000/agendar/demo` e conferir em ate 1 minuto:
`docker compose exec db psql -U agennix -c "select type,status,attempts,error_message from notifications"`.
Sem credenciais Twilio no `backend/.env`, esperado `status = pendente`, `error_message = Twilio não configurado`, virando `falhou` na 3a rodada.

- [ ] **Step 7: Commit**

```bash
git add backend/app/tasks/__init__.py backend/app/__init__.py backend/requirements.txt docker-compose.yml backend/tests/test_notifications.py
git commit -m "backend: comando flask scheduler e servico scheduler no compose"
```

---

### Task 6: Rotulos de celular e README

**Files:**
- Modify: `frontend/src/components/booking/BookingFlow.tsx:3,166` (comentario e `<label>`: "WhatsApp" vira "Celular")
- Modify: `frontend/src/components/dashboard/AppointmentForm.tsx:100,108` (placeholder `Celular (11) 91234-5678`, aria-label `Celular do cliente`, busca `Buscar por nome ou celular`)
- Modify: `backend/app/utils/phone.py` (docstring do modulo e mensagem `Número de celular inválido`)
- Modify: `backend/app/resources/public_booking.py:3` (docstring: "nome e celular")
- Modify: `README.md`

- [ ] **Step 1:** Aplicar as trocas de texto do frontend e do backend acima. Nomes de variaveis e campos JSON (`whatsapp`) nao mudam.
- [ ] **Step 2: README**
  - Linha 5: "lembretes automaticos no WhatsApp" vira "lembretes automaticos por SMS".
  - Status (linhas 7-12): incluir confirmacao e lembrete por SMS entre os implementados; tirar "WhatsApp" dos pendentes.
  - Tabela Stack: `Agendador | APScheduler (lembretes por SMS via Twilio)`.
  - "Como rodar": o `docker compose up` ja sobe o `scheduler`; nova subsecao "SMS (Twilio)": criar conta de teste, verificar o proprio celular em Verified Caller IDs, liberar Brasil em Messaging > Geo Permissions, preencher `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` e `REMINDER_HOURS_BEFORE` no `backend/.env`, `docker compose restart scheduler`. Avisar que a conta de teste prefixa o texto com "Sent from your Twilio trial account".
  - "Proximo passo": dashboard financeiro (5.6).
- [ ] **Step 3:** `cd frontend && npm test && npm run lint`. Esperado: sem erros. `docker compose exec backend pytest`. Esperado: toda a suite passa.
- [ ] **Step 4:** `grep -rniE "whatsapp|evolution" README.md docker-compose.yml backend/.env.example backend/requirements.txt frontend/src/components`. Esperado: so nomes de variavel/campo (`whatsapp`, `setWhatsapp`, `client.whatsapp`), nenhum texto visivel ao usuario.
- [ ] **Step 5: Commit**

```bash
git add frontend/src backend/app/utils/phone.py backend/app/resources/public_booking.py README.md
git commit -m "frontend: rotulos de celular; docs: README com SMS via Twilio"
```
