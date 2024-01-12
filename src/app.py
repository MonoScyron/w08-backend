import json
import os

from typing import Union
from flask import Flask, request
from flask_migrate import Migrate

from db import db
from db import Department, Abnormality, Agent, Project, Ability, Harm, Ego, Clock, Tile

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
mig = Migrate(app, db)

with app.app_context():
    mig.init_app(app)
    db.create_all()


# * Generic responses

def success_response(data: Union[str, dict, list], code=200):
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


# * Routes

@app.route('/')
def hello_world():
    """
    Hello world
    """
    return success_response("Hello world!")


@app.route('/v1/departments/', methods=['GET'])
def get_all_departments():
    all_departments = Department.query.all()
    departments = [dep.serialize() for dep in all_departments]
    return success_response(departments)


@app.route('/v1/abnormalities/', methods=['GET'])
def get_all_abnormalities():
    all_abnormalities = Abnormality.query.all()
    abnormalities = [abnormality.serialize() for abnormality in all_abnormalities]
    return success_response(abnormalities)


@app.route('/v1/agents/', methods=['GET'])
def get_all_agents():
    all_agents = Agent.query.all()
    agents = [agent.serialize() for agent in all_agents]
    return success_response(agents)


@app.route('/v1/abilities/', methods=['GET'])
def get_all_abilities():
    all_abilities = Ability.query.all()
    abilities = [ability.serialize() for ability in all_abilities]
    return success_response(abilities)


@app.route('/v1/harms/', methods=['GET'])
def get_all_harms():
    all_harms = Harm.query.all()
    harms = [harm.serialize() for harm in all_harms]
    return success_response(harms)


@app.route('/v1/egos/', methods=['GET'])
def get_all_egos():
    all_egos = Ego.query.all()
    egos = [ego.serialize() for ego in all_egos]
    return success_response(egos)


@app.route('/v1/clocks/', methods=['GET'])
def get_all_clocks():
    all_clocks = Clock.query.all()
    clocks = [clock.serialize() for clock in all_clocks]
    return success_response(clocks)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
