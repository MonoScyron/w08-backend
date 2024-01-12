#!/bin/bash

flask db init
flask db migrate
flask db upgrade

python src/app.py
