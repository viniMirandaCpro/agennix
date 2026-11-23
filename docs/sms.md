# Notificações por SMS (Twilio)

Referência do que está implementado nas histórias 5.3 (lembrete) e 5.12,
critério 3 (confirmação): como funciona, como configurar e operar, o que se
descobriu da conta de teste do Twilio e o que ficou pendente. O desenho
original e as alternativas descartadas estão em
[specs/2026-11-23-lembretes-sms-design.md](superpowers/specs/2026-11-23-lembretes-sms-design.md).

## O que o cliente recebe

| Situação | SMS |
|---|---|
| Agenda pelo link público (`/agendar/{slug}`) | Confirmação, em até 1 minuto |
| Agendamento feito pelo painel ou pela API | Nenhuma confirmação |
| Agendamento `pendente` ou `confirmado` entra na janela de `REMINDER_HOURS_BEFORE` horas (padrão 2) | Lembrete, em até 1 minuto depois de entrar na janela |
| Agendou já dentro da janela (ex.: às 15h para as 16h) | Só a confirmação; sem lembrete, acabou de agendar |
| Agendamento cancelado, concluído, em atendimento ou "não compareceu" | Nada; o pendente vira `falhou` |
| Remarcado pelo painel (data, hora, profissional ou serviço) | O lembrete antigo é apagado e sai um novo para o horário novo |
| Cliente sem celular cadastrado | Nada |

Textos (sem acento, ver [Decisões](#decisões)), com data e hora no fuso do
estabelecimento e o primeiro nome do cliente:

```
Barbearia Demo: Ola Vini, seu horario de Corte com Carlos esta confirmado para 23/11 as 17:30.
Barbearia Demo: Ola Vini, lembrete: Corte com Carlos em 23/11 as 17:30.
```

## Como funciona

```
agendamento público ──▶ notifications (confirmacao, pendente)
                                     │
serviço scheduler, a cada minuto ────┤ 1. cria os lembretes da janela
   (flask scheduler → run_once)      │ 2. envia os pendentes ──▶ Twilio
                                     ▼
                         enviada  ou  falhou (com error_message)
```

- **Tabela `notifications`** ([modelagem 3.19](modelagem.md#319-notifications--mensagens-enviadas)):
  uma linha por mensagem, `UNIQUE (appointment_id, type)`, então nenhum
  agendamento recebe duas confirmações ou dois lembretes.
- **Confirmação** (`app/services/appointment_service.py`): o
  `create_appointment` com `source == "publico"` grava a linha na mesma
  transação do agendamento. O agendamento nunca espera o Twilio, e um conflito
  de horário não deixa confirmação órfã.
- **Job** (`app/tasks/reminders.py`, `run_once`):
  1. `queue_reminders`: agendamentos `pendente`/`confirmado` com início entre
     agora e agora + N horas, criados antes de `início − N`, com celular e
     ainda sem lembrete. Grava o lembrete com `scheduled_for = início − N`.
  2. `send_pending`: para cada notificação `pendente` com `scheduled_for <= agora`:
     - agendamento fora de `pendente`/`confirmado` → `falhou`, "Agendamento {status}";
     - agendamento que já começou → `falhou`, "Horário já passou";
     - senão envia: sucesso → `enviada`, `sent_at`, `provider_message_id`
       (SID do Twilio); erro → `attempts + 1` e `error_message`, tenta de novo
       no minuto seguinte e vira `falhou` na 3ª tentativa.

     Faz um commit por mensagem: se o processo cair no meio do lote, o que já
     saiu não é reenviado.
- **Remarcação** (`update_appointment`): se mudou horário, profissional ou
  serviço, apaga o lembrete (enviado ou não); o job cria outro na janela nova.
- **Envio** (`app/services/sms_service.py`): `send_sms(to, body)` faz um POST
  na API REST do Twilio (`requests`, sem SDK) e devolve o SID; qualquer recusa
  vira `RuntimeError` com a mensagem do Twilio.
- **Agendador** (`app/tasks/__init__.py`): comando `flask scheduler`
  (APScheduler `BlockingScheduler`, a cada minuto, `max_instances=1`,
  `coalesce=True`), rodando no serviço `scheduler` do docker-compose.

## Configuração

Em `backend/.env` (modelo em `backend/.env.example`):

| Variável | O que é |
|---|---|
| `TWILIO_ACCOUNT_SID` | Console do Twilio, quadro *Account Info* |
| `TWILIO_AUTH_TOKEN` | Mesmo quadro |
| `TWILIO_FROM_NUMBER` | Número **do Twilio** que envia, em E.164 (`+15551234567`). Não é o celular do cliente nem o seu |
| `REMINDER_HOURS_BEFORE` | Antecedência do lembrete em horas inteiras. Padrão 2. Não deixe a variável vazia: `REMINDER_HOURS_BEFORE=` impede o backend de subir |

Depois de mudar o `.env`, recrie o container:

```bash
docker compose up -d scheduler
```

`docker compose restart scheduler` **não** lê o `.env` de novo: o container
continua com as variáveis de quando foi criado. O `restart` serve para mudanças
de código (o agendador não recarrega código sozinho).

Sem credenciais, as mensagens ficam com o erro `Twilio não configurado` e
viram `falhou` na 3ª tentativa. O passo a passo da conta está no
[README](../README.md#sms-twilio).

## Conta de teste do Twilio

Verificado em 23/11/2026 com uma conta de teste real:

- **Só modelos prontos.** O texto do Agennix é recusado com "Invalid template
  name. Trial accounts can only use predefined SMS templates". O `Body` precisa
  ser o nome de um modelo do Twilio: `sms_2fa`, `sms_appointment_reminders`,
  `sms_order_confirmation`, `sms_delivery_updates`, `sms_customer_support`,
  `sms_marketing_promotions`, `sms_event_notifications`, `sms_account_alerts`,
  `sms_feedback_surveys`, `sms_internal_alerts`. O texto desses modelos é fixo
  e não leva nome, serviço nem horário.
- **Só números verificados**, até 5 por conta, e só no país do número usado no
  cadastro da conta.
- **100 SMS grátis** e 30 dias de validade.
- A API não deixa consultar o status de uma mensagem (`403 Forbidden`): para
  saber se chegou, veja o celular ou *Monitor → Logs → Messaging* no console.
- Na conta testada, a API de *Verified Caller IDs* voltou vazia, mas o celular
  usado no cadastro da conta recebeu normalmente.

Para mandar o texto do Agennix é preciso fazer o upgrade da conta. O upgrade
libera texto livre e qualquer destino, mas o número de teste não fica com você:
compre um número e troque `TWILIO_FROM_NUMBER`. O código não muda.

Teste de ponta a ponta possível na conta de teste (chega um SMS com o texto do
modelo, gasta 1 dos 100 grátis):

```bash
docker compose exec -T scheduler python -c '
from app import create_app
from app.services.sms_service import send_sms
with create_app().app_context():
    print(send_sms("+55DDDNUMERO", "sms_appointment_reminders"))'
```

Fontes: [Twilio trial account](https://www.twilio.com/docs/usage/trials),
[Try out Twilio SMS Messaging](https://www.twilio.com/docs/usage/trials/try-out-sms).

## Operação

Ver o que saiu:

```bash
docker compose exec db psql -U agennix -c "
  select n.id, n.type, n.status, n.attempts, n.scheduled_for, n.error_message, a.starts_at
  from notifications n join appointments a on a.id = n.appointment_id
  order by n.id desc limit 20"
```

Reenviar uma que falhou (sai no minuto seguinte, se o agendamento ainda estiver
ativo e não tiver começado):

```sql
update notifications set status = 'pendente', attempts = 0, error_message = null where id = <id>;
```

- Falhas de envio ficam **só no banco** (`error_message`); o
  `docker compose logs scheduler` mostra apenas a linha de início.
- **Nunca rode dois agendadores** contra o mesmo banco (dois `flask scheduler`,
  ou o APScheduler dentro do backend): sem trava de linha, sairiam SMS em dobro.
- `docker compose stop scheduler` demora 10 s: o `flask` como processo 1 do
  container ignora o SIGTERM e o Docker o mata.

## Decisões

| Decisão | Por quê | Custo |
|---|---|---|
| SMS via Twilio em vez de WhatsApp | APIs não oficiais do WhatsApp levam ao banimento do número pela Meta | SMS é pago por mensagem e não tem confirmação de leitura |
| Agendador em processo próprio (`scheduler`) | Dentro do backend, o reloader do `flask --debug` e cada worker do gunicorn criariam outro agendador e SMS em dobro | Mais um container |
| O job cria o lembrete quando o agendamento entra na janela | Cancelamento não precisa de código; remarcação só apaga o lembrete antigo | Job parado por horas: lembretes saem atrasados (ou não saem, se o horário já passou) |
| Confirmação gravada na transação do agendamento, enviada pelo job | O agendamento público nunca espera nem falha por causa do Twilio | Confirmação chega em até 1 minuto, não na hora |
| `requests` direto na API REST, sem o SDK do Twilio | Um único POST não justifica uma dependência | Tratamento de erro feito à mão |
| Texto sem acento | Acento faz o SMS cair de 160 para 70 caracteres por segmento | "horario", "esta", "as" sem acento |
| Remarcação apaga o lembrete em vez de mudar a regra de unicidade | Mudança mínima, sem migração | Perde-se o registro do lembrete antigo |
| Quem remarca dentro da janela recebe outro lembrete | Lembrete com horário errado é pior que dois SMS | Até 2 lembretes para o mesmo agendamento |
| Coluna `clients.whatsapp` mantida com esse nome | Renomear exigiria migração e mexer em todo o frontend | O nome não reflete mais o uso (é o celular) |

## Limites conhecidos e pendências

Antes de produção:

- **Fraude de SMS ("SMS pumping").** O agendamento público não tem limite de
  uso nem captcha e aceita números internacionais (`ponytail:` em
  `app/resources/public_booking.py`). Com conta paga, alguém pode gerar SMS
  para números de tarifa alta. Correção: limite por IP e só aceitar `+55`;
  enquanto isso, deixe só o Brasil liberado em *Geo Permissions*.
- **Tentativas sem espera.** As 3 tentativas acontecem em 3 minutos seguidos:
  uma queda do Twilio de mais de 3 minutos faz os SMS daquele período falharem
  de vez. Erros permanentes (número inválido) também são repetidos, e um
  timeout depois de o Twilio aceitar pode gerar SMS duplicado. Correção:
  adiar `scheduled_for` a cada falha e não repetir erros 4xx.
- **Falhas fora do log.** Correção: `current_app.logger.warning` no `except`
  de `send_pending`.

Menores:

- Erro do Twilio que não vem em JSON (ex.: 502 com HTML) grava a mensagem de
  erro do parser e perde o código HTTP.
- `REMINDER_HOURS_BEFORE=` vazio derruba a inicialização (`int("")`).
- `stop_signal: SIGINT` no serviço `scheduler` acabaria com a espera de 10 s.
- Remarcação feita fora do painel (direto no banco) não gera lembrete novo.
- Cancelar e reativar um agendamento já dentro da janela: o lembrete que virou
  `falhou` no cancelamento não é recriado.
- Um agendador só: para rodar mais de um, buscar os pendentes com
  `FOR UPDATE SKIP LOCKED` (`ponytail:` em `app/tasks/reminders.py`).
- O teste de fuso horário só pega o erro porque a sessão do banco roda em UTC.

Fora do escopo, de propósito: número de envio e antecedência por
estabelecimento, tela de notificações no painel, aviso de remarcação ou
cancelamento, canal e-mail.

## Testes

`backend/tests/test_notifications.py` roda no Postgres de teste e **nunca usa a
rede**: o envio é substituído por um falso (`fake_sender`) e a chamada ao Twilio
por um `requests.post` simulado. Cobre: unicidade e CHECKs da tabela; montagem
da chamada ao Twilio e erros; texto com os cinco dados, sem acento e no fuso
do estabelecimento; confirmação só no agendamento público; criação do lembrete
dentro e fora da janela; cancelado, já começado e cliente sem celular;
tentativas e desistência na 3ª; uma falha não trava as outras; remarcação
refaz o lembrete; comando `flask scheduler` registrado.

```bash
docker compose exec backend pytest tests/test_notifications.py
```
