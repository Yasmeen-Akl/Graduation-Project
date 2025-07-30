from flask import Flask,render_template
from config import Config
from extensions import db
from flask_migrate import Migrate
from routes import main, run_websocket_server
from werkzeug.utils import secure_filename

def create_app():
    app=Flask(__name__)
    app.config.from_object(Config)
    register_resources(app)
    register_extensions(app)
    return app

def register_extensions(app):
    db.init_app(app)
    migrate=Migrate(app,db)

def register_resources(app):
    app.register_blueprint(main)
    

if __name__=='__main__':
    run_websocket_server()
    app= create_app()
    # app.run('127.0.0.1',5555)
    app.run(host='127.0.0.1', port=5555, debug=True, use_reloader=False)