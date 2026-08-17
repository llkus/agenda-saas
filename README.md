# Agenda SaaS

SaaS de agendamento multi-tenant para salões, barbearias e clínicas: painel
web para gerenciar serviços, clientes, disponibilidade e agendamentos, mais
um **agente de IA que atende pelo WhatsApp** — entende o que o cliente quer,
consulta os horários reais e marca o atendimento sozinho, sem fluxo engessado
de menu numérico.

O sistema tem três peças que conversam entre si:

```
Cliente no WhatsApp
        │
        ▼
  Evolution API (self-hosted, conexão real do WhatsApp)
        │  webhook de mensagem recebida
        ▼
      n8n  ──────────────►  Google Gemini (raciocina, decide o que fazer)
        │                          │
        │      chama a ferramenta  │
        ▼                          ▼
  API REST do Flask (/api/v1, autenticada por X-API-Key)
        │
        ▼
   Postgres (dados do negócio: serviços, clientes, agendamentos, mensagens)
        ▲
        │
   Painel web (o dono do estabelecimento usa isso)
```

O painel e o agente de IA **compartilham o mesmo banco e a mesma lógica de
disponibilidade** — um agendamento criado pelo robô aparece na hora no
kanban e na agenda do painel, e vice-versa.

## Por que existe

A maioria das ferramentas de agendamento pra pequenos negócios ou é cara
demais pro tamanho do negócio, ou trata o WhatsApp como um menu de opção
numérica ("digite 1 pra agendar, 2 pra cancelar"). Aqui a aposta é diferente:
um agente de IA de verdade conduz a conversa em linguagem natural, e o
dono do estabelecimento nunca precisa treinar o cliente a "usar o sistema".

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Flask 3 + SQLAlchemy + Flask-Migrate (Alembic) |
| Banco | PostgreSQL (Supabase) |
| Autenticação do painel | JWT em cookie HttpOnly (Flask-JWT-Extended) |
| CSRF | Flask-WTF, exceto o blueprint `api` (autenticado por `X-API-Key`, sem cookie) |
| Rate limiting | Flask-Limiter (login: 10 tentativas/minuto por IP) |
| Frontend | Jinja2 server-rendered + Tailwind (via CDN, sem build step) |
| Automação / orquestração | n8n (self-hosted via Docker) |
| WhatsApp | Evolution API (self-hosted, Baileys) |
| Agente de IA | Google Gemini (`gemini-flash-latest`), plano gratuito |

Frontend sem build step de propósito: é só Jinja + Tailwind Play CDN, então
qualquer editor de texto e um `flask run` bastam pra ver mudanças — sem
`npm install`, sem bundler.

## Modelo de dados

Tudo é isolado por `tenant_id` (um tenant = um estabelecimento). Todas as
queries do painel e da API filtram por tenant explicitamente — não existe
consulta "global" que atravesse estabelecimentos.

- **Tenant** — o estabelecimento. Tem uma `api_key` própria (gerada
  automaticamente) usada pelo n8n pra autenticar na API.
- **User** — quem loga no painel (dono/funcionário).
- **Servico** — nome, duração, preço, ativo/inativo (soft-delete: um serviço
  desativado some das opções de agendamento, mas atendimentos passados que o
  referenciam continuam íntegros).
- **Cliente** — nome + telefone (telefone é único por tenant).
- **Disponibilidade** — janelas recorrentes por dia da semana (ex: "segunda
  09:00–18:00"). É contra isso que o sistema calcula horário livre.
- **Agendamento** — status (`a_confirmar`, `confirmado`, `realizado`,
  `feedback`, `cancelado`), horário, valor (snapshot do preço do serviço no
  momento da criação — se o preço mudar depois, o histórico não é afetado).
  Protegido por um **índice único parcial no Postgres**
  (`tenant_id, data_hora_inicio` onde `status != cancelado`) que impede duas
  reservas simultâneas no mesmo horário mesmo sob corrida de requisições.
- **Mensagem** — log de cada mensagem trocada no WhatsApp (cliente/robô/
  equipe), é o que alimenta a aba **Conversas** do painel.

## O agente de IA

O agente não segue um roteiro fixo. Ele recebe a mensagem do cliente, o
histórico da conversa (memória por telefone) e uma única ferramenta que ele
mesmo decide como usar, com cinco ações possíveis:

`buscar_servicos` · `horarios_disponiveis` · `criar_agendamento` ·
`listar_agendamentos` · `cancelar_agendamento`

O telefone do cliente é sempre injetado automaticamente a partir da sessão
do WhatsApp — o modelo nunca precisa (nem consegue) inventar ou adivinhar
esse dado. O prompt do sistema instrui o agente a sempre confirmar
serviço/data/horário com o cliente antes de criar o agendamento, e a nunca
inventar preço ou disponibilidade — só responder com o que as ferramentas
realmente retornaram.

Está rodando no plano gratuito do Gemini (limite de 5 requisições/minuto) —
suficiente pra validar o fluxo, mas uma assinatura paga é o próximo passo
óbvio antes de qualquer uso em produção real.

## API para o n8n (`/api/v1`)

Autenticada por header `X-API-Key` (a chave do tenant). Sem essa API o n8n
não conversa com o sistema:

| Rota | O que faz |
|---|---|
| `GET /servicos` | Lista serviços ativos |
| `GET /horarios-disponiveis?servico_id=&data=` | Horários livres (HH:MM) num dia |
| `GET /clientes?telefone=` | Busca cliente por telefone |
| `POST /agendamentos` | Cria agendamento (cria o cliente também, se for novo) |
| `GET /agendamentos?telefone=` | Agendamentos futuros ativos de um cliente |
| `POST /agendamentos/<id>/cancelar` | Cancela |
| `POST /mensagens` | Registra uma mensagem trocada (loga no painel) |
| `GET /mensagens?telefone=` | Histórico de mensagens (contexto pro agente) |

## Painel

- **Hoje** — faturamento do mês, ocupação, próximos atendimentos
- **Agenda** — grade semanal visual
- **Agendamentos** — lista do dia com ações de status
- **Kanban** — agendamentos por status, arrastar-e-soltar
- **Clientes** / **Serviços** / **Disponibilidade** — CRUD
- **Conversas** — histórico de atendimentos feitos pelo agente de IA
- **WhatsApp** — QR code de conexão da instância

Design segue um sistema próprio ("Maestro"): fundo escuro com halos radiais
sutis, superfícies em vidro fosco (`backdrop-filter` + fio de luz no topo),
um único acento âmbar por tela, tipografia em só dois pesos (300/500).
Totalmente responsivo — a barra lateral vira uma barra horizontal rolável
em telas de celular.

## Setup local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# preencha SECRET_KEY, JWT_SECRET_KEY (gere com o comando no próprio .env.example)
# e DATABASE_URL com a connection string do seu projeto Supabase

flask db upgrade

# criar o primeiro tenant e usuário admin (não há cadastro público —
# provisionamento é sempre via CLI, de propósito)
flask create-tenant "Nome do Estabelecimento"
flask create-user --tenant-id 1 --nome "Seu Nome" --email voce@exemplo.com --senha "senha-forte"

flask run
```

Pra apagar um tenant (ex: churn de cliente) e todos os dados vinculados a
ele (usuários, agendamentos, financeiro, mensagens etc.):

```bash
flask delete-tenant --tenant-id 1
```

### Ligando o agente de IA (n8n + Evolution API + Gemini)

Isso roda fora do repositório do Flask, como serviços Docker separados:

1. `docker compose up -d` num `docker-compose.yml` com a imagem
   `docker.n8n.io/n8nio/n8n` (porta 5678)
2. Suba uma instância da [Evolution API](https://github.com/EvolutionAPI/evolution-api)
   (self-hosted) e crie uma instância nomeada pro seu tenant
3. Escaneie o QR code em `/painel/whatsapp/`
4. No n8n, monte o workflow: webhook (recebe da Evolution API) → AI Agent
   (Gemini + memória + a ferramenta de agenda) → resposta de volta pela
   Evolution API. O agente chama de volta o Flask via `/api/v1` com a
   `X-API-Key` do tenant.
5. Configure o webhook da Evolution API pra apontar pro webhook do n8n:
   `POST /webhook/set/<instancia>` com `events: ["MESSAGES_UPSERT"]`

Container do Flask e container do n8n em redes Docker diferentes se
enxergam via `host.docker.internal` quando o Flask roda direto no host
(fora de container).

## Testes

```bash
python -m pytest tests/ -v
```

33 testes cobrindo autenticação, CRUD de cada recurso, isolamento
multi-tenant (garantindo que um tenant nunca acessa dado de outro), cálculo
de horários disponíveis, corrida de agendamento simultâneo, exclusão de
tenant em cascata, a API do n8n e
CSRF. Rodam contra SQLite em memória — não tocam o Postgres real.

## Segurança

- Isolamento multi-tenant reforçado em toda query (painel e API)
- Senha com bcrypt, JWT em cookie HttpOnly + SameSite
- CSRF (Flask-WTF) em todo form do painel
- Rate limit no login
- Índice único no banco contra corrida de agendamento duplo
- `SECRET_KEY`/`JWT_SECRET_KEY` obrigatórias — o app recusa subir sem elas
  configuradas (sem fallback fraco tipo `"dev"`)
- Headers básicos de segurança (`X-Frame-Options`, `X-Content-Type-Options`)

## Deploy

Preparado para qualquer plataforma que fale Procfile (Render, Railway,
Heroku):

- `Procfile` roda `flask db upgrade` na fase de release e sobe `gunicorn`
- Configure as variáveis de ambiente do `.env.example` no painel da
  plataforma (nunca commitar `.env`)
- `JWT_COOKIE_SECURE` liga automaticamente quando `FLASK_ENV=production`
- O rate limiter usa armazenamento em memória por padrão — funciona bem com
  um único worker; com múltiplos workers/instâncias, trocar por um backend
  compartilhado (Redis) pra manter os limites consistentes entre eles

## O que ainda não tem

- Cadastro público de tenant (provisionamento é manual via CLI, decisão
  intencional pro estágio atual do projeto)
- Deploy real em produção (só a esteira pronta via Procfile)
- Papéis/permissões por usuário (o campo `role` existe no model mas ainda
  não restringe nada)
- Assinatura paga do Gemini (rodando no free tier, 5 req/min)

## Estrutura de etapas

Projeto construído por etapas incrementais (esqueleto → models → auth →
CRUD → agendamentos → API n8n → kanban → agenda → dashboard → polimento →
agente de IA) — cada uma commitada separadamente. Ver histórico do git para
o racional de cada decisão.
