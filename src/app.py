import json
import os

import logging

from psycopg2 import IntegrityError
from sqlalchemy import inspect
from sqlalchemy.exc import StatementError

from flask import Flask, request, abort
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload

from db import db, data_json_path
from db import Facility, Department, Abnormality, Agent, Project, Ability, Harm, Ego, Clock, Tile

logging.basicConfig(level=logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(stream_handler)

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
mig = Migrate(app, db)

with app.app_context():
    mig.init_app(app)
    db.create_all()

required_fields = {}
relationship_fields = {}
tablename_to_model = {}
for db_model in [Facility, Department, Abnormality, Agent, Project, Ability, Harm, Ego, Clock, Tile]:
    tablename_to_model[db_model.__tablename__] = db_model
    inspector = inspect(db_model)

    columns = inspector.columns.values()
    required_fields[db_model.__tablename__] = [column.name for column in columns if
                                               not column.nullable and column.default is None and column.name != 'id']

    relationship_fields[db_model.__tablename__] = inspector.relationships.keys()

with open(data_json_path, 'r') as file:
    file_data = json.load(file)
    departments = file_data.get('departments')
    containment_tiles = file_data.get('containment_tiles')
    fields_to_column = file_data.get('fields_to_column')
    field_to_tablename = file_data.get('field_to_tablename')


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
    except (IntegrityError, StatementError) as e:
        db.session.rollback()
        return failure_response(f'{str(e)}', 400)
    except Exception as e:
        db.session.rollback()
        return failure_response(str(e), 500)


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


def update_relationships(data, model_instance, model: db.Model):
    """
    Update the relationships of a model instance based on the data provided in the request.
    :param data: Data from the request containing the relationships to be updated.
    :param model_instance: Instance to update the relationships of
    :param model: Model representing the table in the database
    :return: None
    """
    model_assign_fields = fields_to_column[model.__tablename__]
    for k in data.keys():
        if k in model_assign_fields.keys():
            relationship_id = data.get(k)

            if not type(relationship_id) is list:
                if not (relationship := tablename_to_model[field_to_tablename[k]].query.get(relationship_id)):
                    return failure_response(
                        f'Row not found in table \'{field_to_tablename[k]}\' for id={relationship_id}'
                    )
                setattr(model_instance, model_assign_fields[k], relationship)
            else:
                relationship_list = []
                for r_id in relationship_id:
                    if not (relationship := tablename_to_model[field_to_tablename[k]].query.get(r_id)):
                        return failure_response(f'Row not found in table \'{field_to_tablename[k]}\' for id={r_id}')
                    relationship_list.append(relationship)
                setattr(model_instance, model_assign_fields[k], relationship_list)


def get_all_from_model(model: db.Model):
    """
    Retrieve all objects from the specified SQLAlchemy model and serialize them
    :param model: Model representing the database table
    :return: Success response containing serialized objects
    """
    all_objs = model.query.all()
    objs = [obj.serialize() for obj in all_objs]
    return success_response(objs)


def get_one_from_model(model_id, model: db.Model):
    """
    Retrieve a single object from the specified SQLAlchemy model
    :param model_id: Unique identifier of the object to be retrieved
    :param model: Model representing the database table
    :return: Success response containing the serialized object if found. Otherwise, returns failure response.
    """
    obj = model.query.get(model_id)
    if not obj:
        return failure_response(f'Row not found for id: {model_id}')
    return success_response(obj.serialize())


def create_model(data, model: db.Model):
    """
    Create a new row of the table represented by the SQLAlchemy model and add it to the database
    :param data: Object containing the data to for creating new row
    :param model: Model representing the database table to create a new row for
    :return: Success response if instance successfully created. Otherwise, returns failure response.
    """
    if has_fields := check_required_fields(data, model):
        return has_fields

    new_model = model(**data)
    db.session.add(new_model)
    update_relationships(data, new_model, model)

    db.session.commit()
    return success_response(new_model.serialize(), 201)


def delete_model_by_id(model_id: int, model: db.Model):
    """
    Deletes a row from the table represented by the SQLAlchemy model
    :param model_id: Unique identifier of the row to be deleted
    :param model: Model representing the database table being updated
    :return: Success response if instance successfully deleted. Otherwise, returns failure response.
    """
    model_instance = model.query
    for relationship in relationship_fields[model.__tablename__]:
        model_instance = model_instance.options(joinedload(getattr(model, relationship)))
    model_instance = model_instance.get(model_id)
    if model_instance:
        db.session.delete(model_instance)
        db.session.commit()
        return success_response(model_instance.serialize())
    else:
        return failure_response(f'Row not found for id: {model_id}')


def edit_model_by_id(model_id, data, model: db.Model):
    """
    Edits an existing row of the table represented by the SQLAlchemy model
    :param model_id: Unique identifier of the row to be edited
    :param data: Object containing the data to be updated
    :param model: Model representing the database table to be updated
    :return: Success response containing the updated object. Otherwise, returns failure response.
    """
    queried_model = model.query.get(model_id)
    if not queried_model:
        return failure_response(f'Row not found for id: {model_id}')

    # Update columns
    table = model.metadata.tables[model.__tablename__]
    for k, v in data.items():
        if k not in table.columns:
            return failure_response(f'Column \'{k}\' not found', 400)
        setattr(queried_model, k, v)

    update_relationships(data, queried_model, model)

    db.session.commit()
    return success_response(queried_model.serialize())


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
    return catch_exception_wrapper(create_model, data, Department)


@app.route('/v1/abnormalities/', methods=['POST'])
def create_abnormality():
    data = request.json
    return catch_exception_wrapper(create_model, data, Abnormality)


@app.route('/v1/agents/', methods=['POST'])
def create_agent():
    data = request.json
    return catch_exception_wrapper(create_model, data, Agent)


@app.route('/v1/projects/', methods=['POST'])
def create_project():
    data = request.json
    return catch_exception_wrapper(create_model, data, Project)


@app.route('/v1/abilities/', methods=['POST'])
def create_ability():
    data = request.json
    return catch_exception_wrapper(create_model, data, Ability)


@app.route('/v1/harms/', methods=['POST'])
def create_harm():
    data = request.json
    return catch_exception_wrapper(create_model, data, Harm)


@app.route('/v1/egos/', methods=['POST'])
def create_ego():
    data = request.json
    return catch_exception_wrapper(create_model, data, Ego)


@app.route('/v1/clocks/', methods=['POST'])
def create_clock():
    data = request.json
    return catch_exception_wrapper(create_model, data, Clock)


# * Delete routes

# @app.route('/v1/departments/<int:department_id>/', methods=['DELETE'])
@app.route('/v1/abnormalities/<int:abnormality_id>/', methods=['DELETE'])
def delete_abnormality(abnormality_id):
    return catch_exception_wrapper(delete_model_by_id, abnormality_id, Abnormality)


@app.route('/v1/agents/<int:agent_id>/', methods=['DELETE'])
def delete_agent(agent_id):
    return catch_exception_wrapper(delete_model_by_id, agent_id, Agent)


@app.route('/v1/projects/<int:project_id>/', methods=['DELETE'])
def delete_project(project_id):
    return catch_exception_wrapper(delete_model_by_id, project_id, Project)


@app.route('/v1/abilities/<int:ability_id>/', methods=['DELETE'])
def delete_ability(ability_id):
    return catch_exception_wrapper(delete_model_by_id, ability_id, Ability)


@app.route('/v1/harms/<int:harm_id>/', methods=['DELETE'])
def delete_harm(harm_id):
    return catch_exception_wrapper(delete_model_by_id, harm_id, Harm)


@app.route('/v1/egos/<int:ego_id>/', methods=['DELETE'])
def delete_ego(ego_id):
    return catch_exception_wrapper(delete_model_by_id, ego_id, Ego)


@app.route('/v1/clocks/<int:clock_id>/', methods=['DELETE'])
def delete_clock(clock_id):
    return catch_exception_wrapper(delete_model_by_id, clock_id, Clock)


# * Edit routes

@app.route('/v1/facilities/<int:facility_id>/', methods=['POST'])
def edit_facility(facility_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, facility_id, data, Facility)


@app.route('/v1/departments/<int:department_id>/', methods=['POST'])
def edit_department(department_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, department_id, data, Department)


@app.route('/v1/abnormalities/<int:abnormality_id>/', methods=['POST'])
def edit_abnormality(abnormality_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, abnormality_id, data, Abnormality)


@app.route('/v1/agents/<int:agent_id>/', methods=['POST'])
def edit_agent(agent_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, agent_id, data, Agent)


@app.route('/v1/projects/<int:project_id>/', methods=['POST'])
def edit_project(project_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, project_id, data, Project)


@app.route('/v1/abilities/<int:ability_id>/', methods=['POST'])
def edit_ability(ability_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, ability_id, data, Ability)


@app.route('/v1/harms/<int:harm_id>/', methods=['POST'])
def edit_harm(harm_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, harm_id, data, Harm)


@app.route('/v1/egos/<int:ego_id>/', methods=['POST'])
def edit_ego(ego_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, ego_id, data, Ego)


@app.route('/v1/clocks/<int:clock_id>/', methods=['POST'])
def edit_clock(clock_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, clock_id, data, Clock)


@app.route('/v1/tiles/<int:tile_id>/', methods=['POST'])
def edit_tile(tile_id):
    data = request.json
    return catch_exception_wrapper(edit_model_by_id, tile_id, data, Tile)


# * Runtime

def facility_init():
    with app.app_context():
        try:
            facility = Facility.query.all()
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
            deps = Department.query.all()
            if len(deps) != 5:
                Department.query.delete()

                for name, dep_id in departments.items():
                    new_dep = Department(id=dep_id, name=name)
                    db.session.add(new_dep)

                db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, "Failed to set up departments")


def tiles_init():
    with app.app_context():
        try:
            tiles = Tile.query.all()
            if len(tiles) != 448:
                Tile.query.delete()

                for i in range(16):
                    containment_list = containment_tiles[str(i)] if str(i) in containment_tiles else []
                    for j in range(28):
                        new_tile = Tile(x=j, y=i, can_place_containment=(j in containment_list))
                        db.session.add(new_tile)

                db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, "Failed to set up tiles")


if __name__ == "__main__":
    facility_init()
    departments_init()
    tiles_init()
    app.run(host="0.0.0.0", port=5000, debug=True)
