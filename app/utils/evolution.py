import requests
from flask import current_app


def _config():
    return (
        current_app.config["EVOLUTION_API_URL"].rstrip("/"),
        current_app.config["EVOLUTION_API_KEY"],
        current_app.config["EVOLUTION_INSTANCE"],
    )


def status_conexao():
    base_url, api_key, instance = _config()
    if not (base_url and api_key and instance):
        return {"state": "nao_configurado"}

    try:
        resp = requests.get(
            f"{base_url}/instance/connectionState/{instance}",
            headers={"apikey": api_key},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("instance", {})
    except (requests.RequestException, ValueError) as exc:
        return {"state": "erro", "erro": str(exc)}


def enviar_mensagem(telefone: str, texto: str) -> bool:
    base_url, api_key, instance = _config()
    if not (base_url and api_key and instance):
        return False

    try:
        resp = requests.post(
            f"{base_url}/message/sendText/{instance}",
            headers={"apikey": api_key},
            json={"number": telefone, "text": texto},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def buscar_mensagens(remote_jid: str, pagina: int) -> dict:
    """Busca uma página do histórico de mensagens de uma conversa (já
    armazenado no banco da própria Evolution API, vindo do celular
    conectado). 50 mensagens por página."""
    base_url, api_key, instance = _config()
    if not (base_url and api_key and instance):
        return {"total": 0, "pages": 0, "records": []}

    resp = requests.post(
        f"{base_url}/chat/findMessages/{instance}",
        headers={"apikey": api_key},
        json={"where": {"key": {"remoteJid": remote_jid}}, "page": pagina},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("messages", {"total": 0, "pages": 0, "records": []})


def obter_qrcode():
    base_url, api_key, instance = _config()
    if not (base_url and api_key and instance):
        return None

    try:
        resp = requests.get(
            f"{base_url}/instance/connect/{instance}",
            headers={"apikey": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("base64") or data.get("qrcode", {}).get("base64")
    except (requests.RequestException, ValueError):
        return None
