import itertools

from app.extensions import db
from app.models import Cliente, Mensagem, RemetenteMensagem
from app.utils import whatsapp_import

_ids = itertools.count()


def _pagina(records, pages=1, page=1):
    return {"total": len(records), "pages": pages, "currentPage": page, "records": records}


def _msg(texto, from_me, timestamp):
    return {
        "id": f"msg-{next(_ids)}",
        "key": {"fromMe": from_me},
        "message": {"conversation": texto},
        "messageTimestamp": timestamp,
    }


def _mock_igual_nos_dois_campos(mensagens):
    """Simula um contato 'antigo' (sem LID): a mesma busca por remoteJid e
    por remoteJidAlt bate as mesmas mensagens (dedupe deve evitar duplicar)."""
    return lambda jid, pagina, campo="remoteJid": _pagina(mensagens)


def _mock_so_remote_jid_alt(mensagens):
    """Simula um contato migrado pro endereçamento por LID: só a busca por
    remoteJidAlt encontra alguma coisa, remoteJid (o ID opaco) não bate com
    nada porque construímos o jid a partir do telefone, não do LID."""
    def _buscar(jid, pagina, campo="remoteJid"):
        return _pagina(mensagens) if campo == "remoteJidAlt" else _pagina([])
    return _buscar


def test_importa_mensagens_de_texto_do_cliente(app, tenant, monkeypatch):
    cliente = Cliente(tenant_id=tenant.id, nome="Ana", telefone="5511988887777")
    db.session.add(cliente)
    db.session.commit()

    mensagens = [
        _msg("oi, quero agendar", False, 1000),
        _msg("Claro! Qual serviço?", True, 1001),
    ]
    monkeypatch.setattr(whatsapp_import, "buscar_mensagens", _mock_igual_nos_dois_campos(mensagens))

    total = whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=500)

    assert total == 2
    salvas = Mensagem.query.filter_by(tenant_id=tenant.id).order_by(Mensagem.criado_em).all()
    assert [m.texto for m in salvas] == ["oi, quero agendar", "Claro! Qual serviço?"]
    assert salvas[0].remetente == RemetenteMensagem.CLIENTE
    assert salvas[1].remetente == RemetenteMensagem.EQUIPE


def test_importa_contato_migrado_pra_lid_via_remote_jid_alt(app, tenant, monkeypatch):
    """Contatos que o WhatsApp migrou pro endereçamento por LID guardam o
    telefone real em remoteJidAlt, não em remoteJid (que vira um ID opaco
    tipo '123...@lid'). A importação tem que achar essas mensagens mesmo
    assim, buscando também por remoteJidAlt."""
    cliente = Cliente(tenant_id=tenant.id, nome="Suellen", telefone="558585978807")
    db.session.add(cliente)
    db.session.commit()

    mensagens = [_msg("Teste", False, 1000)]
    monkeypatch.setattr(whatsapp_import, "buscar_mensagens", _mock_so_remote_jid_alt(mensagens))

    total = whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=500)

    assert total == 1
    assert Mensagem.query.filter_by(tenant_id=tenant.id).first().texto == "Teste"


def test_ignora_mensagens_sem_texto_ex_midia(app, tenant, monkeypatch):
    cliente = Cliente(tenant_id=tenant.id, nome="Ana", telefone="5511988887777")
    db.session.add(cliente)
    db.session.commit()

    mensagens = [
        {"id": "m1", "key": {"fromMe": False}, "message": {"imageMessage": {}}, "messageTimestamp": 1000},
        _msg("oi", False, 1001),
    ]
    monkeypatch.setattr(whatsapp_import, "buscar_mensagens", _mock_igual_nos_dois_campos(mensagens))

    total = whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=500)

    assert total == 1
    assert Mensagem.query.filter_by(tenant_id=tenant.id).count() == 1


def test_e_idempotente_rodar_duas_vezes_nao_duplica(app, tenant, monkeypatch):
    cliente = Cliente(tenant_id=tenant.id, nome="Ana", telefone="5511988887777")
    db.session.add(cliente)
    db.session.commit()

    mensagens = [_msg("oi", False, 1000)]
    monkeypatch.setattr(whatsapp_import, "buscar_mensagens", _mock_igual_nos_dois_campos(mensagens))

    whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=500)
    segunda = whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=500)

    assert segunda == 0
    assert Mensagem.query.filter_by(tenant_id=tenant.id).count() == 1


def test_respeita_limite_por_cliente(app, tenant, monkeypatch):
    cliente = Cliente(tenant_id=tenant.id, nome="Ana", telefone="5511988887777")
    db.session.add(cliente)
    db.session.commit()

    mensagens = [_msg(f"msg {i}", False, 1000 + i) for i in range(10)]
    monkeypatch.setattr(whatsapp_import, "buscar_mensagens", _mock_igual_nos_dois_campos(mensagens))

    total = whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=3)

    assert total == 3
    assert Mensagem.query.filter_by(tenant_id=tenant.id).count() == 3


def test_importar_historico_tenant_cobre_todos_os_clientes(app, tenant, monkeypatch):
    c1 = Cliente(tenant_id=tenant.id, nome="Ana", telefone="5511988887777")
    c2 = Cliente(tenant_id=tenant.id, nome="Beto", telefone="5511977776666")
    db.session.add_all([c1, c2])
    db.session.commit()

    monkeypatch.setattr(
        whatsapp_import, "buscar_mensagens", _mock_igual_nos_dois_campos([_msg("oi", False, 1000)])
    )

    resultado = whatsapp_import.importar_historico_tenant(tenant.id)

    assert resultado == {"5511988887777": 1, "5511977776666": 1}


def test_isolamento_multi_tenant_na_importacao(app, tenant, outro_tenant, monkeypatch):
    cliente = Cliente(tenant_id=tenant.id, nome="Ana", telefone="5511988887777")
    db.session.add(cliente)
    db.session.commit()

    monkeypatch.setattr(
        whatsapp_import, "buscar_mensagens", _mock_igual_nos_dois_campos([_msg("oi", False, 1000)])
    )
    whatsapp_import.importar_historico_cliente(tenant.id, cliente, limite=500)

    assert Mensagem.query.filter_by(tenant_id=outro_tenant.id).count() == 0
