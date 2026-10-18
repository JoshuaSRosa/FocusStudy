from flask import Blueprint, jsonify, request
from flask.wrappers import Response
from flask_jwt_extended import create_access_token, get_jwt_identity, verify_jwt_in_request
# import database as db
from psycopg2.extras import RealDictConnection
from psycopg2.extensions import cursor
import hashlib
import re


db_sim = {"users": [{"username": "User1", "email": "email@gmail.com", "name": "Algum Nome", "password": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"}, {"username": "User2", "email": "outroemail@email.com", "name": "Outro Nome", "password": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}]} # Senhas: 123; abc

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
        return jsonify({"status", "error - wrong forms request"}), 401

    # DADOS REAIS
    # conn = db.get_db_connection()
    # if not conn:
    #     return jsonify(status="error", error="failed connection with database"), 401 # Erro ao se conectar com o DB

    # cur: cursor = conn.cursor(cursor_factory=RealDictConnection)
    # query = r"SELECT username, email FROM users WHERE email = ? OR username = ?"
    # cur.execute(query, (email, username))
    # data = cur.fetchall()
    # if len(data) == 2:
    #     return jsonify(status="error", error="usuário e email já cadastrados")
    # elif data[0] == username:
    #     return jsonify(status="error", error="usuário já cadastrado")
    # elif data[1] == email:
    #     return jsonify(status="error", error="email já cadastrado")
    
    # DADOS TESTE
    data = db_sim["users"]
    for d in data: # DADOS TESTE
        u = d["username"]
        e = d["email"]
        if e == email and u == username:
            return jsonify(status="error", error="usuário e email já cadastrados!"), 401
        elif u == username:
            return jsonify(status="error", error="usuário já cadastrado"), 401
        elif e == email:
            return jsonify(status="error", error="email já cadastrado"), 401

    # Validar EMAIL, USERNAME, NAME e PASSWORD
    if not validate_user(username):
        return jsonify(status="error", error="username regex failed"), 401
    if not validate_email(email):
        return jsonify(status="error", error="email regex failed"), 401
    if not validate_name(name):
        return jsonify(status="error", error="name regex failed"), 401
    if not validate_password(password):
        return jsonify(status="error", error="password regex failed"), 401

    # DADOS REAIS
    # query = r"INSERT INTO users VALUES (?, ?, ?, ?)"
    # cur.execute(query, (username, email, name, hashlib.sha256(password.encode()).hexdigest()))

    # db.release_db_connection(conn)

    # DADOS TESTE
    db_sim["users"].append({"username": username, "email": email, "name": name, "password": hashlib.sha256(password.encode()).hexdigest()})

    return jsonify(status="success")
    
@api.route("/login", methods=["POST"])
def login() -> Response:
    user = request.form.get("user", None)
    password = request.form.get("password", None)

    if verify_jwt_in_request(optional=True) is not None:
        return jsonify(status="sucess", logged_as=get_jwt_identity()), 200

    hash_password = hashlib.sha256(password.encode()).hexdigest()

    for u in db_sim["users"]:
        print(u)
        if u["email"] != user and u["username"] != user:
            continue

        if u["password"] == hash_password:
            access_token = create_access_token(identity=user)
            return jsonify(status="sucess", access_token=access_token, logged_as=user), 200

    return jsonify(status="error", error="failed login"), 401
