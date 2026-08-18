from datetime import datetime, timezone

from app.utils.dates import horario_local


def test_converte_utc_para_horario_local():
    dt_utc = datetime(2026, 8, 18, 0, 33, tzinfo=timezone.utc)
    local = horario_local(dt_utc)
    assert local.strftime("%H:%M") == "21:33"
    assert local.strftime("%d/%m/%Y") == "17/08/2026"


def test_trata_datetime_sem_tzinfo_como_utc():
    dt_naive = datetime(2026, 8, 18, 0, 33)
    local = horario_local(dt_naive)
    assert local.strftime("%H:%M") == "21:33"


def test_none_retorna_none():
    assert horario_local(None) is None
