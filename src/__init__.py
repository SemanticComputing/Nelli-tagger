from flask import json
from flask import Flask
from flask_cors import CORS, cross_origin
#from flask_sqlalchemy import SQLAlchemy
#from flask_migrate import Migrate

# flask basic configurations
app = Flask(__name__)

# flask using cors headers
cors = CORS(app)

# database configurations
#from src.database.config import Config, ProdConfig, DevConfig, TestConfig
#app.config.from_object(Config)

#if app.config["ENV"] == "production":
#    app.config.from_object(ProdConfig)
#else:
#    app.config.from_object(DevConfig)

#db = SQLAlchemy(app)
#migrate = Migrate(app, db)

#from src.database import models

#models.init_db()


#project_dir = os.path.dirname(os.path.abspath(__file__))
#database_file = "sqlite:///{}".format(os.path.join(project_dir, "feedback.db"))

#app.config["SQLALCHEMY_DATABASE_URI"] = database_file

