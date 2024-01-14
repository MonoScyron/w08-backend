import json
import os

from psycopg2 import IntegrityError
from sqlalchemy.exc import StatementError

from flask import Flask, request, abort
from flask_migrate import Migrate

from db import db, data_json_path
from db import Facility, Department, Abnormality, Agent, Project, Ability, Harm, Ego, Clock, Tile

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
mig = Migrate(app, db)

with app.app_context():
    mig.init_app(app)
    db.create_all()

with open(data_json_path, 'r') as file:
    file_data = json.load(file)
    required_fields = file_data.get('required_fields')
    departments = file_data.get('departments')


# * Generic responses

def success_response(data, code=200):
    """
    Generalized success response function
    :param data: Object to be wrapped as JSON
    :param code: Success response code
    :return: Data as JSON and response code
    """
    return json.dumps(data), code


def failure_response(message: str, code=404):
    """
    Generalized failure response function
    :param message: Error message to be wrapped as JSON
    :param code: Error response code
    :return: Error message wrapped as JSON and response code
    """
    return json.dumps({"error": message}), code


# * Generic functions

def catch_exception_wrapper(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except IntegrityError as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)
    except StatementError as e:
        db.session.rollback()
        return failure_response(f'{str(e).splitlines().pop(0)}', 400)
    except Exception as e:
        db.session.rollback()
        return failure_response(str(e), 500)


def get_all_from_model(model: db.Model):
    """
    Retrieve all objects from the specified SQLAlchemy model and serialize them
    :param model: Model representing the database table
    :return: Success response containing serialized objects
    """
    all_objs = db.session.query(model).all()
    objs = [obj.serialize() for obj in all_objs]
    return success_response(objs)


def get_one_from_model(model_id, model: db.Model):
    """
    Retrieve a single object from the specified SQLAlchemy model
    :param model_id: Unique identifier of the object to be retrieved
    :param model: Model representing the database table
    :return: Success response containing the serialized object if found. Otherwise, returns failure response.
    """
    obj = db.session.query(model).get(model_id)
    if not obj:
        return failure_response(f'Not found for id: {model_id}')
    return success_response(obj.serialize())


def check_required_fields(data, model: db.Model):
    """
    Validate the presence of required fields in the request for a specific SQLAlchemy model
    :param data: Request data to be validated in JSON format
    :param model: Model representing the database table
    :return: Failure response if required fields are missing. Otherwise, returns None.
    """
    model_required_fields = required_fields[model.__tablename__]
    if any(field not in data.keys() for field in model_required_fields):
        missing_fields = [field for field in model_required_fields if field not in data.keys()]
        return failure_response(f'Missing required fields: {missing_fields}', 400)
    return None


def create_model(data, model: db.Model):
    """
    Create a new row of the table represented by the SQLAlchemy model and add it to the database
    :param data: Object containing the data to for creating new row
    :param model: Model representing the database table to create a new row for
    :return: Success response if instance successfully created. Otherwise, returns failure response.
    """
    try:
        new_model = model(**data)
        db.session.add(new_model)
        db.session.commit()
        return success_response(new_model.serialize(), 201)

    except IntegrityError as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)
    except StatementError as e:
        db.session.rollback()
        return failure_response(f'{str(e).splitlines().pop(0)}', 400)
    except Exception as e:
        db.session.rollback()
        return failure_response(str(e), 500)


def delete_model_by_id(model_id: int, model: db.Model):
    """
    Deletes a row from the table represented by the SQLAlchemy model
    :param model_id: Unique identifier of the row to be deleted
    :param model: Model representing the database table from which the instance is being deleted
    :return: Success response if instance successfully deleted. Otherwise, returns failure response.
    """
    try:
        obj = db.session.query(model).get(model_id)
        if obj:
            db.session.delete(obj)
            db.session.commit()
            return success_response(obj.serialize())
        else:
            return failure_response(f'Not found for id: {model_id}')

    except IntegrityError as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)
    except Exception as e:
        db.session.rollback()
        return failure_response(str(e), 500)


def edit_model_by_id(model_id, data, model: db.Model):
    """
    Edits an existing row of the table represented by the SQLAlchemy model
    :param model_id: Unique identifier of the row to be edited
    :param data: Object containing the data to be updated
    :param model: Model representing the database table to be updated
    :return: Success response containing the updated object. Otherwise, returns failure response.
    """
    try:
        queried_model = db.session.query(model).get(model_id)
        if not queried_model:
            return failure_response(f'Not found for id: {model_id}')
        queried_model.update(**data)
        db.session.commit()
        return success_response(queried_model.serialize())

    except IntegrityError as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)
    except StatementError as e:
        db.session.rollback()
        return failure_response(f'{str(e).splitlines().pop(0)}', 400)
    except Exception as e:
        db.session.rollback()
        return failure_response(str(e), 500)


@app.route('/')
def hello_world():
    return success_response("Hello world!")


# * Get all routes

@app.route('/v1/departments/', methods=['GET'])
def get_all_departments():
    return get_all_from_model(Department)


@app.route('/v1/abnormalities/', methods=['GET'])
def get_all_abnormalities():
    return get_all_from_model(Abnormality)


@app.route('/v1/agents/', methods=['GET'])
def get_all_agents():
    return get_all_from_model(Agent)


@app.route('/v1/projects/', methods=['GET'])
def get_all_projects():
    return get_all_from_model(Project)


@app.route('/v1/abilities/', methods=['GET'])
def get_all_abilities():
    return get_all_from_model(Ability)


@app.route('/v1/harms/', methods=['GET'])
def get_all_harms():
    return get_all_from_model(Harm)


@app.route('/v1/egos/', methods=['GET'])
def get_all_egos():
    return get_all_from_model(Ego)


@app.route('/v1/clocks/', methods=['GET'])
def get_all_clocks():
    return get_all_from_model(Clock)


@app.route('/v1/tiles/', methods=['GET'])
def get_all_tiles():
    return get_all_from_model(Tile)


# * Get 1 routes

@app.route('/v1/facilities/<int:facility_id>/', methods=['GET'])
def get_facility(facility_id):
    return get_one_from_model(facility_id, Facility)


@app.route('/v1/departments/<int:department_id>/', methods=['GET'])
def get_department(department_id):
    return get_one_from_model(department_id, Department)


@app.route('/v1/abnormalities/<int:abnormality_id>/', methods=['GET'])
def get_abnormality(abnormality_id):
    return get_one_from_model(abnormality_id, Abnormality)


@app.route('/v1/agents/<int:agent_id>/', methods=['GET'])
def get_agent(agent_id):
    return get_one_from_model(agent_id, Agent)


@app.route('/v1/projects/<int:project_id>/', methods=['GET'])
def get_project(project_id):
    return get_one_from_model(project_id, Project)


@app.route('/v1/abilities/<int:ability_id>/', methods=['GET'])
def get_ability(ability_id):
    return get_one_from_model(ability_id, Ability)


@app.route('/v1/harms/<int:harm_id>/', methods=['GET'])
def get_harm(harm_id):
    return get_one_from_model(harm_id, Harm)


@app.route('/v1/egos/<int:ego_id>/', methods=['GET'])
def get_ego(ego_id):
    return get_one_from_model(ego_id, Ego)


@app.route('/v1/clocks/<int:clock_id>/', methods=['GET'])
def get_clock(clock_id):
    return get_one_from_model(clock_id, Clock)


@app.route('/v1/tiles/<int:tile_id>/', methods=['GET'])
def get_tile(tile_id):
    return get_one_from_model(tile_id, Tile)


# * Create routes

# @app.route('/v1/departments/', methods=['POST'])
def create_department():
    data = request.json
    if has_fields := check_required_fields(data, Department):
        return has_fields
    return create_model(data, Department)


@app.route('/v1/abnormalities/', methods=['POST'])
def create_abnormality():
    data = request.json
    if has_fields := check_required_fields(data, Abnormality):
        return has_fields
    return create_model(data, Abnormality)


@app.route('/v1/agents/', methods=['POST'])
def create_agent():
    data = request.json
    if has_fields := check_required_fields(data, Agent):
        return has_fields

    # Assign agent to department
    department_id = data.get('department_id')
    if not (department := db.session.query(Department).get(department_id)):
        return failure_response(f'Department not found for id: {department_id}')
    data.update({'department': department})

    return create_model(data, Agent)


@app.route('/v1/projects/', methods=['POST'])
def create_project():
    data = request.json
    if has_fields := check_required_fields(data, Project):
        return has_fields

    # Assign project to department
    department_id = data.get('department_id')
    if not (department := db.session.query(Department).get(department_id)):
        return failure_response(f'Department not found for id: {department_id}')
    del data['department_id']

    try:
        new_project = Project(**data)
        department.projects.append(new_project)
        db.session.commit()
        return success_response(new_project.serialize(), 201)

    except IntegrityError as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)
    except StatementError as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)  # .splitlines().pop(0)
    except Exception as e:
        db.session.rollback()
        return failure_response(str(e), 500)


@app.route('/v1/abilities/', methods=['POST'])
def create_ability():
    data = request.json
    if has_fields := check_required_fields(data, Ability):
        return has_fields
    return create_model(data, Ability)


@app.route('/v1/harms/', methods=['POST'])
def create_harm():
    data = request.json
    if has_fields := check_required_fields(data, Harm):
        return has_fields

    # Assign harm to agent
    agent_id = data.get('agent_id')
    if not (agent := db.session.query(Agent).get(agent_id)):
        return failure_response(f'Agent not found for id: {agent_id}')
    data.update({'agent': agent})

    return create_model(data, Harm)


@app.route('/v1/egos/', methods=['POST'])
def create_ego():
    data = request.json
    if has_fields := check_required_fields(data, Ego):
        return has_fields

    # Assign ego to abno
    abnormality_id = data.get('abnormality_id')
    if not (abnormality := db.session.query(Abnormality).get(abnormality_id)):
        return failure_response(f'Abnormality not found for id: {abnormality_id}')
    data.update({'abnormality': abnormality})

    return create_model(data, Ego)


@app.route('/v1/clocks/', methods=['POST'])
def create_clock():
    data = request.json
    if has_fields := check_required_fields(data, Clock):
        return has_fields
    return create_model(data, Clock)


# * Delete routes

# @app.route('/v1/departments/<int:department_id>/', methods=['DELETE'])
def delete_department(department_id):
    return delete_model_by_id(department_id, Department)


@app.route('/v1/abnormalities/<int:abnormality_id>/', methods=['DELETE'])
def delete_abnormality(abnormality_id):
    return delete_model_by_id(abnormality_id, Abnormality)


@app.route('/v1/agents/<int:agent_id>/', methods=['DELETE'])
def delete_agent(agent_id):
    return delete_model_by_id(agent_id, Agent)


@app.route('/v1/projects/<int:project_id>/', methods=['DELETE'])
def delete_project(project_id):
    return delete_model_by_id(project_id, Project)


@app.route('/v1/abilities/<int:ability_id>/', methods=['DELETE'])
def delete_ability(ability_id):
    return delete_model_by_id(ability_id, Ability)


@app.route('/v1/harms/<int:harm_id>/', methods=['DELETE'])
def delete_harm(harm_id):
    return delete_model_by_id(harm_id, Harm)


@app.route('/v1/egos/<int:ego_id>/', methods=['DELETE'])
def delete_ego(ego_id):
    return delete_model_by_id(ego_id, Ego)


@app.route('/v1/clocks/<int:clock_id>/', methods=['DELETE'])
def delete_clock(clock_id):
    return delete_model_by_id(clock_id, Clock)


# * Edit routes

@app.route('/v1/facilities/<int:facility_id>/', methods=['POST'])
def edit_facility(facility_id):
    data = request.json
    return edit_model_by_id(facility_id, data, Facility)


@app.route('/v1/departments/<int:department_id>/', methods=['POST'])
def edit_department(department_id):
    data = request.json
    return edit_model_by_id(department_id, data, Department)


@app.route('/v1/abnormalities/<int:abnormality_id>/', methods=['POST'])
def edit_abnormality(abnormality_id):
    data = request.json
    return edit_model_by_id(abnormality_id, data, Abnormality)


@app.route('/v1/agents/<int:agent_id>/', methods=['POST'])
def edit_agent(agent_id):
    data = request.json
    return edit_model_by_id(agent_id, data, Agent)


@app.route('/v1/projects/<int:project_id>/', methods=['POST'])
def edit_project(project_id):
    data = request.json
    return edit_model_by_id(project_id, data, Project)


@app.route('/v1/abilities/<int:ability_id>/', methods=['POST'])
def edit_ability(ability_id):
    data = request.json
    return edit_model_by_id(ability_id, data, Ability)


@app.route('/v1/harms/<int:harm_id>/', methods=['POST'])
def edit_harm(harm_id):
    data = request.json
    return edit_model_by_id(harm_id, data, Harm)


@app.route('/v1/egos/<int:ego_id>/', methods=['POST'])
def edit_ego(ego_id):
    data = request.json
    return edit_model_by_id(ego_id, data, Ego)


@app.route('/v1/clocks/<int:clock_id>/', methods=['POST'])
def edit_clock(clock_id):
    data = request.json
    return edit_model_by_id(clock_id, data, Clock)


@app.route('/v1/tiles/<int:tile_id>/', methods=['POST'])
def edit_tile(tile_id):
    data = request.json
    return edit_model_by_id(tile_id, data, Tile)


# * Runtime

def facility_init():
    with app.app_context():
        try:
            facility = db.session.query(Facility).all()
            if len(facility) < 1:
                facility = Facility()
                db.session.add(facility)
                db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, "Failed to set up facility")


def departments_init():
    with app.app_context():
        try:
            deps = db.session.query(Department).all()
            if len(deps) != 5:
                db.session.query(Department).delete()

                for name, dep_id in departments.items():
                    new_dep = Department(id=dep_id, name=name)
                    db.session.add(new_dep)

                db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, "Failed to set up departments")


def tiles_init():
    # TODO: Initialize all tiles in tiles table (reference departments_init)
    pass


if __name__ == "__main__":
    facility_init()
    departments_init()
    app.run(host="0.0.0.0", port=5000, debug=True)
