from flask import Flask, request
from db import db
from db import Department, Abnormality, Agent, Project, Ability, Harm, Ego, Clock, Tile

app = Flask(__name__)
db_filename = "db"

app.config[
    "SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://postgres:postgres@postgres:5432/" + db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
# migrate = Migrate(src, db)
with app.app_context():
    db.create_all()

    new_dep = Department(name="Testing", buffs="test buff")
    db.session.add(new_dep)
    db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
