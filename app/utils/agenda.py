from datetime import date, datetime, time, timedelta

from app.models import Agendamento, Disponibilidade, Servico, StatusAgendamento

INTERVALO_MINUTOS = 15

STATUS_OCUPAM_HORARIO = (
    StatusAgendamento.A_CONFIRMAR,
    StatusAgendamento.CONFIRMADO,
    StatusAgendamento.REALIZADO,
)


def horarios_disponiveis(tenant_id: int, servico_id: int, dia: date) -> list[time]:
    servico = Servico.query.filter_by(id=servico_id, tenant_id=tenant_id, ativo=True).first()
    if not servico:
        return []

    duracao = timedelta(minutes=servico.duracao_min)

    janelas = Disponibilidade.query.filter_by(tenant_id=tenant_id, dia_semana=dia.weekday()).all()
    if not janelas:
        return []

    inicio_dia = datetime.combine(dia, time.min)
    fim_dia = datetime.combine(dia + timedelta(days=1), time.min)

    ocupados = Agendamento.query.filter(
        Agendamento.tenant_id == tenant_id,
        Agendamento.status.in_(STATUS_OCUPAM_HORARIO),
        Agendamento.data_hora_inicio >= inicio_dia,
        Agendamento.data_hora_inicio < fim_dia,
    ).all()

    agora = datetime.now()
    disponiveis = []

    for janela in janelas:
        candidato = datetime.combine(dia, janela.hora_inicio)
        fim_janela = datetime.combine(dia, janela.hora_fim)

        while candidato + duracao <= fim_janela:
            candidato_fim = candidato + duracao

            if candidato > agora:
                conflita = any(
                    candidato < ag.data_hora_fim and candidato_fim > ag.data_hora_inicio
                    for ag in ocupados
                )
                if not conflita and candidato.time() not in disponiveis:
                    disponiveis.append(candidato.time())

            candidato += timedelta(minutes=INTERVALO_MINUTOS)

    return sorted(disponiveis)
