import json

from typing import Union
from flask import Flask, request
from flask_migrate import Migrate, upgrade, migrate
from db import db
from db import Department, Abnormality, Agent, Project, Ability, Harm, Ego, Clock, Tile

app = Flask(__name__)
db_filename = "db"

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@postgres:5432/" + db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

mig = Migrate(app, db)
db.init_app(app)
with app.app_context():
    db.create_all()
    mig.migrate()
    mig.upgrade()


def success_response(data: Union[str, dict], code=200):
    """
    Generalized success response function
    :param data: Data to be wrapped as JSON
    :param code: Success response code
    :return: Data as JSON, code
    """
    return json.dumps(data), code


def failure_response(message: str, code=404):
    """
    Generalized failure response function
    :param message: Message to be wrapped as JSON
    :param code: Error response code
    :return: Error message wrapped as JSON, code
    """
    return json.dumps({"error": message}), code


@app.route("/")
def hello_world():
    """
    Endpoint for hello world
    """
    return success_response("Hello world!")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
