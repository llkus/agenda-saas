from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Agendamento, Recorrencia, StatusAgendamento
from app.utils.agenda import horarios_disponiveis


@dataclass
class Ocorrencia:
    data: date
    cabe: bool
    impedimento: str | None = None


def proxima_data(a_partir_de: date, dia_semana: int) -> date:
    delta = (dia_semana - a_partir_de.weekday()) % 7
    return a_partir_de + timedelta(days=delta)


def planejar_ocorrencias(recorrencia: Recorrencia, dias_a_frente: int = 60) -> list[Ocorrencia]:
    hoje = date.today()
    inicio = max(hoje, recorrencia.gerado_ate + timedelta(days=1)) if recorrencia.gerado_ate else hoje
    limite = hoje + timedelta(days=dias_a_frente)

    ocorrencias: list[Ocorrencia] = []
    candidata = proxima_data(inicio, recorrencia.dia_semana)

    while candidata <= limite:
        disponiveis = horarios_disponiveis(recorrencia.tenant_id, recorrencia.servico_id, candidata)
        ja_tem = Agendamento.query.filter(
            Agendamento.tenant_id == recorrencia.tenant_id,
            Agendamento.cliente_id == recorrencia.cliente_id,
            Agendamento.status != StatusAgendamento.CANCELADO,
            db.func.date(Agendamento.data_hora_inicio) == candidata,
        ).first()

        if ja_tem:
            ocorrencias.append(Ocorrencia(candidata, cabe=False, impedimento="Cliente já tem agendamento neste dia"))
        elif recorrencia.hora not in disponiveis:
            ocorrencias.append(Ocorrencia(candidata, cabe=False, impedimento="Horário ocupado ou fora do expediente"))
        else:
            ocorrencias.append(Ocorrencia(candidata, cabe=True))

        candidata += timedelta(weeks=recorrencia.intervalo_semanas)

    return ocorrencias


def gerar_agendamentos(recorrencia: Recorrencia, dias_a_frente: int = 60) -> int:
    """Cria um Agendamento para cada ocorrência que cabe. Retorna quantos foram criados."""
    servico = recorrencia.servico
    criados = 0
    ultima_data = recorrencia.gerado_ate

    for oc in planejar_ocorrencias(recorrencia, dias_a_frente):
        if oc.cabe:
            inicio = datetime.combine(oc.data, recorrencia.hora)
            fim = inicio + timedelta(minutes=servico.duracao_min)
            db.session.add(
                Agendamento(
                    tenant_id=recorrencia.tenant_id,
                    cliente_id=recorrencia.cliente_id,
                    servico_id=recorrencia.servico_id,
                    data_hora_inicio=inicio,
                    data_hora_fim=fim,
                    valor=servico.preco,
                    status=StatusAgendamento.A_CONFIRMAR,
                )
            )
            criados += 1
        ultima_data = oc.data

    if ultima_data:
        recorrencia.gerado_ate = ultima_data
    db.session.commit()
    return criados
