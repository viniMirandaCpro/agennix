# Lembretes e confirmacao por SMS (historia 5.3 + criterio 3 da 5.12)

## Intencao

O cliente recebe um SMS de confirmacao quando agenda pelo link publico e um
lembrete `REMINDER_HOURS_BEFORE` horas (padrao 2) antes de qualquer
agendamento, para reduzir faltas. O canal era WhatsApp via Evolution API;
foi trocado por SMS via Twilio porque APIs nao oficiais do WhatsApp levam ao
banimento do numero pela Meta.

## Metas

- 5.3.1 Mensagem com nome do cliente, servico, profissional, dia e horario.
- 5.3.2 Lembrete com antecedencia pre-definida (`REMINDER_HOURS_BEFORE`).
- 5.3.3 Numero validado em E.164 (ja feito por `normalize_whatsapp`).
- 5.3 implicito: nunca enviar a mesma mensagem duas vezes.
- 5.12.3 Confirmacao automatica ao agendar pelo link publico.

## Nao-metas

- Numero de envio por estabelecimento (todos usam o numero Twilio do `.env`).
- Antecedencia configuravel por estabelecimento (fica global no `.env`).
- Tela de notificacoes no painel.
- Aviso de remarcacao ou cancelamento.
- Canal e-mail.
- Rejeitar telefone fixo na validacao: o Twilio recusa e o erro fica gravado
  em `notifications.error_message`.

## Anti-metas

- SMS em dobro para o mesmo agendamento.
- Lembrete de agendamento cancelado ou que ja comecou.
- Falha do Twilio derrubar ou atrasar a criacao do agendamento.

## Restricoes

- Twilio em conta de teste: so envia para numeros verificados e prefixa o
  texto com "Sent from your Twilio trial account". Envio para o Brasil precisa
  estar liberado em Geo Permissions no console.
- SMS com acento cai de 160 para 70 caracteres por segmento: o texto sai sem
  acento.
- Testes rodam no Postgres real, sem rede: o envio e substituido por fake.

## Abordagens

**Onde roda o agendador**

| | Abordagem | Troca |
|---|---|---|
| **Escolhida** | Processo proprio `flask scheduler` (APScheduler `BlockingScheduler`), servico `scheduler` no docker-compose | Um unico processo agenda; mais um container |
| Descartada | APScheduler dentro do `create_app` | O reloader do `flask --debug` e cada worker do gunicorn criam um agendador a mais; exige guarda fragil |
| Descartada | `flask send-notifications` disparado por cron do sistema | Precisa de cron no container; APScheduler ja e a escolha do README |

**Quando o lembrete vira linha em `notifications`**

| | Abordagem | Troca |
|---|---|---|
| **Escolhida** | O job, a cada minuto, cria o lembrete dos agendamentos que entraram na janela e envia na mesma rodada | Cancelamento nao precisa de codigo; remarcacao so apaga o lembrete antigo (ver Design) |
| Descartada | Criar o lembrete ao agendar e atualizar `scheduled_for` a cada remarcacao | Mais pontos de codigo em `update_appointment` e mais casos para errar |

**Chamada ao Twilio**: `requests.post` na API REST (`requests` ja instalado),
em vez do SDK `twilio` (dependencia nova para uma chamada HTTP).

O usuario escolheu SMS e Twilio. As demais escolhas acima foram do Claude, com
o usuario delegando o como.

## Design

**Modelo** `app/models/notification.py` conforme a secao 3.19 da modelagem:
`TenantMixin`, `TimestampMixin`, CHECKs de `type` (`confirmacao`, `lembrete`),
`channel` (`sms`, `email`) e `status` (`pendente`, `enviada`, `falhou`),
`UNIQUE (appointment_id, type)` e indice `(status, scheduled_for)`. Migracao
Alembic nova.

**Confirmacao**: `create_appointment` com `source == "publico"` adiciona,
na mesma transacao do agendamento, uma `Notification(type="confirmacao",
channel="sms", destination=client.whatsapp, scheduled_for=agora)`. O envio
fica com o job (sai em ate 1 minuto), assim o agendamento nunca espera o
Twilio.

**Job** `app/tasks/reminders.py`, `run_once(now)`:

1. Enfileira lembretes: agendamentos `pendente`/`confirmado`, com
   `now < starts_at <= now + N`, criados antes de `starts_at - N`, cliente com
   numero e sem lembrete ainda. Cria `Notification(type="lembrete",
   scheduled_for=starts_at - N)`. Quem agendou dentro da janela nao recebe
   lembrete (acabou de agendar).
2. Envia pendentes com `scheduled_for <= now`, cada uma uma vez por rodada,
   commit a cada mensagem (uma queda no meio do lote nao reenvia o que saiu).
   Sem trava de linha: o servico `scheduler` e um processo so, com
   `max_instances=1`.
   Agendamento fora de `pendente`/`confirmado`: `falhou` com
   "Agendamento {status}", sem enviar. Agendamento que ja comecou (job parado
   ou tentativas atrasadas): `falhou` com "Horário já passou", sem enviar.
   Sucesso: `enviada`, `sent_at`, `provider_message_id`. Erro: `attempts + 1`,
   `error_message`; vira `falhou` na 3a tentativa, senao tenta no proximo
   minuto.

**Remarcacao**: `update_appointment` apaga o lembrete do agendamento quando
muda horario, servico ou profissional (o texto antigo ficou errado). O job
cria outro na nova janela; um lembrete pendente nao sai com dias de
antecedencia. Custo: o registro do lembrete antigo se perde.

**Envio** `app/services/sms_service.py` (substitui `whatsapp_service.py`):

- `send_sms(to, body) -> sid`: POST em
  `https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json`, basic auth
  `(SID, TOKEN)`, `From`/`To`/`Body`, timeout 10 s. Resposta de erro vira
  `RuntimeError` com a mensagem do Twilio; sem credenciais,
  `RuntimeError("Twilio nao configurado")`.
- `message_for(notification)`: texto sem acento, data e hora no fuso do
  estabelecimento, primeiro nome do cliente.
  - Confirmacao: `{Estab}: Ola {Nome}, seu horario de {Servico} com {Prof} esta confirmado para {dd/mm} as {HH:MM}.`
  - Lembrete: `{Estab}: Ola {Nome}, lembrete: {Servico} com {Prof} em {dd/mm} as {HH:MM}.`

**Agendador** `app/tasks/__init__.py`: comando `flask scheduler`
(`BlockingScheduler`, `run_once` a cada minuto, `max_instances=1`,
`coalesce=True`, dentro de `app.app_context()`), registrado no `create_app`
como o `seed`.

**Configuracao**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
`TWILIO_FROM_NUMBER` e `REMINDER_HOURS_BEFORE` (int, padrao 2) em `config.py` e
`backend/.env.example`; bloco da Evolution removido do `.env.example` e do
`docker-compose.yml`, que ganha o servico `scheduler`.

**Interface**: rotulos "WhatsApp" viram "Celular" no `BookingFlow` e no
`AppointmentForm`; o erro do backend vira "Numero de celular invalido". A
coluna `clients.whatsapp` e o nome `normalize_whatsapp` ficam como estao.

**README**: textos de WhatsApp viram SMS; passo a passo do Twilio (conta de
teste, verificar o celular, liberar Brasil em Geo Permissions); servico
`scheduler`; proximo passo passa a ser o dashboard financeiro (5.6).

**Testes** `tests/test_notifications.py`, com `send_sms` substituido por fake:
confirmacao so no agendamento publico; texto com os cinco dados e sem acento;
lembrete criado e enviado uma vez so em duas rodadas; sem lembrete para
cancelado, para agendamento criado dentro da janela e fora da janela; falha
incrementa tentativas e vira `falhou` na 3a; `send_sms` monta a chamada certa
e sem credenciais falha.

## Deixado para quem implementa

Nomes de funcoes internas, texto das docstrings e a ordem exata das colunas na
migracao.
