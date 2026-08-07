from datetime import datetime


def parse_data(data_str, padrao=None):
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return padrao
