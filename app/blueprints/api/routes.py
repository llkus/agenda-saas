from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models import Agendamento, Cliente, Servico, StatusAgendamento
from app.utils.agenda import horarios_disponiveis
from app.utils.api_auth import require_api_key

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

STATUS_ATIVOS = (StatusAgendamento.A_CONFIRMAR, StatusAgendamento.CONFIRMADO)


def _parse_data(data_str):
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@api_bp.route("/servicos")
@require_api_key
def listar_servicos():
    servicos = (
        Servico.query.filter_by(tenant_id=g.tenant.id, ativo=True).order_by(Servico.nome).all()
    )
    return jsonify(
        [
            {"id": s.id, "nome": s.nome, "duracao_min": s.duracao_min, "preco": str(s.preco)}
            for s in servicos
        ]
    )


@api_bp.route("/horarios-disponiveis")
@require_api_key
def horarios_disponiveis_view():
    servico_id = request.args.get("servico_id", type=int)
    dia = _parse_data(request.args.get("data"))

    if not servico_id or not dia:
        return jsonify({"erro": "parâmetros servico_id e data são obrigatórios"}), 400

    horarios = horarios_disponiveis(g.tenant.id, servico_id, dia)
    return jsonify([h.strftime("%H:%M") for h in horarios])


@api_bp.route("/clientes")
@require_api_key
def buscar_cliente():
    telefone = request.args.get("telefone", "").strip()
    if not telefone:
        return jsonify({"erro": "parâmetro telefone é obrigatório"}), 400

    cliente = Cliente.query.filter_by(tenant_id=g.tenant.id, telefone=telefone).first()
    if not cliente:
        return jsonify({"erro": "cliente não encontrado"}), 404

    return jsonify({"id": cliente.id, "nome": cliente.nome, "telefone": cliente.telefone})


@api_bp.route("/agendamentos", methods=["POST"])
@require_api_key
def criar_agendamento():
    payload = request.get_json(silent=True) or {}

    nome = (payload.get("nome") or "").strip()
    telefone = (payload.get("telefone") or "").strip()
    servico_id = payload.get("servico_id")
    data_str = payload.get("data", "")
    horario_str = payload.get("horario", "")

    erros = []
    if not telefone:
        erros.append("telefone é obrigatório")

    servico = None
    if not servico_id:
        erros.append("servico_id é obrigatório")
    else:
        servico = Servico.query.filter_by(id=servico_id, tenant_id=g.tenant.id, ativo=True).first()
        if not servico:
            erros.append("servico_id inválido")

    dia = _parse_data(data_str)
    if not dia:
        erros.append("data inválida (use YYYY-MM-DD)")

    hora = None
    try:
        hora = datetime.strptime(horario_str, "%H:%M").time()
    except ValueError:
        erros.append("horario inválido (use HH:MM)")

    if erros:
        return jsonify({"erro": "; ".join(erros)}), 400

    disponiveis = horarios_disponiveis(g.tenant.id, servico.id, dia)
    if hora not in disponiveis:
        return jsonify({"erro": "horário não disponível"}), 409

    cliente = Cliente.query.filter_by(tenant_id=g.tenant.id, telefone=telefone).first()
    if not cliente:
        if not nome:
            return jsonify({"erro": "nome é obrigatório para cadastrar um novo cliente"}), 400
        cliente = Cliente(tenant_id=g.tenant.id, nome=nome, telefone=telefone)
        db.session.add(cliente)
        db.session.flush()

    inicio = datetime.combine(dia, hora)
    fim = inicio + timedelta(minutes=servico.duracao_min)

    agendamento = Agendamento(
        tenant_id=g.tenant.id,
        cliente_id=cliente.id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=fim,
        valor=servico.preco,
        status=StatusAgendamento.A_CONFIRMAR,
    )
    db.session.add(agendamento)
    db.session.commit()

    return (
        jsonify(
            {
                "id": agendamento.id,
                "cliente": cliente.nome,
                "servico": servico.nome,
                "data_hora_inicio": inicio.isoformat(),
                "data_hora_fim": fim.isoformat(),
                "valor": str(agendamento.valor),
                "status": agendamento.status.value,
            }
        ),
        201,
    )


@api_bp.route("/agendamentos")
@require_api_key
def listar_agendamentos_cliente():
    telefone = request.args.get("telefone", "").strip()
    if not telefone:
        return jsonify({"erro": "parâmetro telefone é obrigatório"}), 400

    cliente = Cliente.query.filter_by(tenant_id=g.tenant.id, telefone=telefone).first()
    if not cliente:
        return jsonify([])

    agendamentos = (
        Agendamento.query.filter(
            Agendamento.tenant_id == g.tenant.id,
            Agendamento.cliente_id == cliente.id,
            Agendamento.data_hora_inicio >= datetime.now(),
            Agendamento.status.in_(STATUS_ATIVOS),
        )
        .order_by(Agendamento.data_hora_inicio)
        .all()
    )

    return jsonify(
        [
            {
                "id": ag.id,
                "servico": ag.servico.nome,
                "data_hora_inicio": ag.data_hora_inicio.isoformat(),
                "status": ag.status.value,
            }
            for ag in agendamentos
        ]
    )


@api_bp.route("/agendamentos/<int:agendamento_id>/cancelar", methods=["POST"])
@require_api_key
def cancelar_agendamento(agendamento_id):
    agendamento = Agendamento.query.filter_by(id=agendamento_id, tenant_id=g.tenant.id).first()
    if not agendamento:
        return jsonify({"erro": "agendamento não encontrado"}), 404

    agendamento.status = StatusAgendamento.CANCELADO
    db.session.commit()
    return jsonify({"id": agendamento.id, "status": agendamento.status.value})
