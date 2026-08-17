from datetime import datetime

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
