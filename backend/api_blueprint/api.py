from flask import Blueprint, jsonify, request
from flask.wrappers import Response
from flask_jwt_extended import create_access_token, get_jwt_identity, verify_jwt_in_request
from psycopg2 import errors
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
import database as db
import re


api = Blueprint("api", __name__, url_prefix="/api")

#===========
# AUX FUNCS=
#===========

def validate_user(user: str) -> bool:
    """Apenas letras, números e Underline - Não permite espaços em branco - Entre 3 e 20 caracteres"""
    pat = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
    if pat.match(user):
        return True
    return False

def validate_email(email: str) -> bool:
    """Padrão universal nome@dominio.com - Permite pontos, hífens etc antes do @ - Garante ao menos 1 arroba no endereço"""
    pat = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    if pat.match(email):
        return True
    return False

def validate_password(password: str) -> bool:
    """1 letra maiúscula - 1 letra minúscula - 1 número - 1 caractere especial - Pelo menos 8 caracteres"""
    pat = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$")
    if pat.match(password):
        return True
    return False

def validate_name(name: str) -> bool:
    """Suporte a nome e sobrenome - Suporte a acentuação - Não aceita caracteres especiais como !, @, _"""
    pat = re.compile(r"^[A-Za-zÀ-ÿ]+(?: [A-Za-zÀ-ÿ]+)+$")
    if pat.match(name):
        return True
    return False

def db_unavailable() -> tuple[Response, int]:
    return jsonify(status="error", error="failed connection with database"), 503

#========
# ROUTES=
#========

@api.route("/health", methods=["GET"])
def health() -> Response:
    return jsonify({"status": "ok"})

@api.route("/register", methods=["POST"])
def register() -> Response:
    username = request.form.get("username", None)
    email = request.form.get("email", None)
    password = request.form.get("password", None)
    name = request.form.get("name", None)

    if not all([username, email, password, name]): # Se faltar algum parâmetro, retorna erro
        return jsonify(status="error", error="wrong forms request"), 401

    # Validar EMAIL, USERNAME, NAME e PASSWORD
    if not validate_user(username):
        return jsonify(status="error", error="username regex failed"), 401
    if not validate_email(email):
        return jsonify(status="error", error="email regex failed"), 401
    if not validate_name(name):
        return jsonify(status="error", error="name regex failed"), 401
    if not validate_password(password):
        return jsonify(status="error", error="password regex failed"), 401

    conn = db.get_db_connection()
    if not conn:
        return db_unavailable()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT username, email FROM users WHERE username = %s OR email = %s",
                (username, email),
            )
            rows = cur.fetchall()
            usuario_existe = any(r["username"] == username for r in rows)
            email_existe = any(r["email"] == email for r in rows)

            if usuario_existe and email_existe:
                return jsonify(status="error", error="usuário e email já cadastrados!"), 401
            if usuario_existe:
                return jsonify(status="error", error="usuário já cadastrado"), 401
            if email_existe:
                return jsonify(status="error", error="email já cadastrado"), 401

            cur.execute(
                "INSERT INTO users (username, email, name, password) VALUES (%s, %s, %s, %s)",
                (username, email, name, generate_password_hash(password)),
            )
        conn.commit()
    except errors.UniqueViolation:
        # Outro cadastro com o mesmo usuario/email entrou entre o SELECT e o INSERT.
        conn.rollback()
        return jsonify(status="error", error="usuário ou email já cadastrado"), 401
    except Exception:
        conn.rollback()
        raise
    finally:
        db.release_db_connection(conn)

    return jsonify(status="success")

@api.route("/login", methods=["POST"])
def login() -> Response:
    user = request.form.get("user", None)
    password = request.form.get("password", None)

    if verify_jwt_in_request(optional=True) is not None:
        return jsonify(status="sucess", logged_as=get_jwt_identity()), 200

    if not user or not password:
        return jsonify(status="error", error="wrong forms request"), 401

    conn = db.get_db_connection()
    if not conn:
        return db_unavailable()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT username, password FROM users WHERE username = %s OR email = %s",
                (user, user),
            )
            row = cur.fetchone()
    finally:
        db.release_db_connection(conn)

    if row and check_password_hash(row["password"], password):
        username = row["username"]
        access_token = create_access_token(identity=username)
        return jsonify(status="sucess", access_token=access_token, logged_as=username), 200

    return jsonify(status="error", error="failed login"), 401
