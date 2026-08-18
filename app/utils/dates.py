from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ_LOCAL = ZoneInfo("America/Fortaleza")

MESES_ABREV = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]
MESES_COMPLETOS = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def parse_data(data_str, padrao=None):
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return padrao


def mes_abreviado_pt(data) -> str:
    return f"{MESES_ABREV[data.month - 1]}/{data.strftime('%y')}"


def mes_completo_pt(data) -> str:
    return f"{MESES_COMPLETOS[data.month - 1]}/{data.year}"


def horario_local(dt):
    """Converte um datetime salvo em UTC (padrão do banco) pro horário de
    Brasília/Fortaleza (UTC-3), pra exibir no painel. Datas antigas salvas
    sem tzinfo são tratadas como UTC (era o único jeito de gravar antes)."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_LOCAL)
