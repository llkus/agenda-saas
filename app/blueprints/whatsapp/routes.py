from flask import Blueprint, flash, jsonify, redirect, url_for
from flask_jwt_extended import jwt_required

from app.utils.evolution import desconectar, obter_qrcode, status_conexao

whatsapp_bp = Blueprint("whatsapp", __name__, url_prefix="/painel/whatsapp")


@whatsapp_bp.route("/status")
@jwt_required()
def status():
    return jsonify(status_conexao())


@whatsapp_bp.route("/desconectar", methods=["POST"])
@jwt_required()
def desconectar_route():
    if desconectar():
        flash("WhatsApp desconectado.", "success")
    else:
        flash("Não foi possível desconectar agora, tente de novo.", "error")
    return redirect(url_for("conversas.listar"))


@whatsapp_bp.route("/qrcode")
@jwt_required()
def qrcode():
    imagem = obter_qrcode()
    if not imagem:
        return jsonify({"qrcode": None}), 200
    return jsonify({"qrcode": imagem})
