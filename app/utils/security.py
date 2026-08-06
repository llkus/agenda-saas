from passlib.hash import bcrypt


def hash_senha(senha: str) -> str:
    return bcrypt.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.verify(senha, senha_hash)
