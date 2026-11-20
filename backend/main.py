from flask import Flask, Blueprint
from api_blueprint.api import api
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret"
jwt = JWTManager(app)

app.register_blueprint(api)

print(app.url_map)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080 ,debug=True)
