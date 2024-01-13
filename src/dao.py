"""
Data access object
"""

from db import db
from db import Department


def get_department_id_by_name(name: str):
    """
    Get department id by name
    :param name: Department name
    :return: Department id
    """
    return db.session.query(Department).filter(Department.department_name == name).first()
