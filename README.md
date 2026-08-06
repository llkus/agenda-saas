# Agenda SaaS

SaaS de agendamento multi-tenant (salões, barbearias, clínicas). Backend Flask +
painel Jinja2/Tailwind. Integração com WhatsApp fica por conta de um n8n
externo, que consome a API REST autenticada por `X-API-Key`.

## Stack

- Flask 3 + SQLAlchemy + Flask-Migrate (Alembic)
- Postgres (Supabase)
- Autenticação do painel: JWT em cookie HttpOnly (Flask-JWT-Extended)
- CSRF: Flask-WTF (`CSRFProtect`), exceto no blueprint `api` (autenticado por
  `X-API-Key`, sem cookie de sessão)
- Frontend: Jinja2 server-rendered + Tailwind via CDN (sem build step)

## Setup local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# preencha SECRET_KEY, JWT_SECRET_KEY (gere com o comando no próprio .env.example)
# e DATABASE_URL com a connection string do seu projeto Supabase

flask db upgrade

# criar o primeiro tenant e usuário admin (não há cadastro público)
flask create-tenant "Nome do Estabelecimento"
flask create-user --tenant-id 1 --nome "Seu Nome" --email voce@exemplo.com --senha "senha-forte"

flask run
```

## Testes

```bash
python -m pytest tests/ -v
```

Os testes rodam contra SQLite em memória (fixture `app` em `tests/conftest.py`),
sem tocar no banco Postgres real.

## Deploy

Preparado para qualquer plataforma que fale Procfile (Render, Railway, Heroku):

- `Procfile` roda `flask db upgrade` na fase de release e sobe `gunicorn`
- Configure as variáveis de ambiente do `.env.example` no painel da
  plataforma (nunca commitar `.env`)
- `JWT_COOKIE_SECURE` liga automaticamente quando `FLASK_ENV=production`

## Estrutura de etapas

Projeto construído por etapas incrementais (esqueleto → models → auth → CRUD →
agendamentos → API n8n → kanban → agenda → dashboard → polimento). Cada etapa
foi commitada separadamente — ver histórico do git para o racional de cada uma.
