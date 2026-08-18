from datetime import datetime, timezone

from app.extensions import db
from app.models import Cliente, Mensagem, RemetenteMensagem
from app.utils.evolution import buscar_mensagens

LIMITE_PADRAO_POR_CLIENTE = 500


def _remote_jid(telefone: str) -> str:
    digitos = "".join(c for c in telefone if c.isdigit())
    return f"{digitos}@s.whatsapp.net"


def _extrair_texto(mensagem: dict) -> str | None:
    corpo = mensagem.get("message") or {}
    if "conversation" in corpo:
        return corpo["conversation"]
    if "extendedTextMessage" in corpo:
        return corpo["extendedTextMessage"].get("text")
    return None


def _ja_importada(tenant_id: int, telefone: str, texto: str, criado_em: datetime) -> bool:
    return (
        Mensagem.query.filter_by(
            tenant_id=tenant_id, telefone=telefone, texto=texto, criado_em=criado_em
        ).first()
        is not None
    )


def _buscar_paginas(remote_jid: str, campo: str, limite: int) -> list[dict]:
    registros = []
    pagina = 1
    total_paginas = 1

    while pagina <= total_paginas and len(registros) < limite:
        resultado = buscar_mensagens(remote_jid, pagina, campo=campo)
        total_paginas = resultado.get("pages", 1) or 1
        registros.extend(resultado.get("records", []))
        pagina += 1

    return registros


def importar_historico_cliente(tenant_id: int, cliente: Cliente, limite: int) -> int:
    """Importa o histórico de mensagens de texto de um cliente (via
    telefone) pra dentro da nossa tabela `mensagens`. Ignora mídia (áudio,
    imagem, figurinha) porque `Mensagem.texto` só guarda texto. Idempotente:
    pode rodar de novo sem duplicar (checa tenant+telefone+texto+timestamp).

    Busca por `remoteJid` (contatos antigos, telefone direto) e por
    `remoteJidAlt` (contatos migrados pro endereçamento por LID do
    WhatsApp, onde `remoteJid` vira um ID opaco) e junta os dois,
    deduplicando pelo id interno da mensagem na Evolution."""
    remote_jid = _remote_jid(cliente.telefone)
    brutos = _buscar_paginas(remote_jid, "remoteJid", limite) + _buscar_paginas(remote_jid, "remoteJidAlt", limite)

    vistos = set()
    registros = []
    for msg in brutos:
        if msg["id"] in vistos:
            continue
        vistos.add(msg["id"])
        registros.append(msg)

    importadas = 0
    for msg in registros:
        if importadas >= limite:
            break

        texto = _extrair_texto(msg)
        if not texto:
            continue

        criado_em = datetime.fromtimestamp(msg["messageTimestamp"], tz=timezone.utc)
        if _ja_importada(tenant_id, cliente.telefone, texto, criado_em):
            continue

        remetente = RemetenteMensagem.EQUIPE if msg["key"]["fromMe"] else RemetenteMensagem.CLIENTE
        db.session.add(
            Mensagem(
                tenant_id=tenant_id,
                cliente_id=cliente.id,
                telefone=cliente.telefone,
                remetente=remetente,
                texto=texto,
                criado_em=criado_em,
            )
        )
        importadas += 1

    db.session.commit()
    return importadas


def importar_historico_tenant(tenant_id: int, limite_por_cliente: int = LIMITE_PADRAO_POR_CLIENTE) -> dict[str, int]:
    resultado = {}
    for cliente in Cliente.query.filter_by(tenant_id=tenant_id).all():
        resultado[cliente.telefone] = importar_historico_cliente(tenant_id, cliente, limite_por_cliente)
    return resultado
