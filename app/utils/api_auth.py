from functools import wraps

from flask import g, jsonify, request

from app.models import Tenant


def require_api_key(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"erro": "header X-API-Key ausente"}), 401

        tenant = Tenant.query.filter_by(api_key=api_key).first()
        if not tenant:
            return jsonify({"erro": "API key inválida"}), 401

        g.tenant = tenant
        return view(*args, **kwargs)

    return wrapper
