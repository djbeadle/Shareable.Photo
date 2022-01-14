from flask import Flask, Blueprint, g
import sqlite3, uuid

try:
  from config import config, DevelopmentConfig, ProductionConfig
except ModuleNotFoundError as e:
  print('')
  print('ERROR: You forgot to make a copy of the "config-example.py" file called "config.py"')
  print('       Your application will NOT work until you do so.')
  print('')

"""
If you have another file in this directory and want to import it you must
prefix the import statement with the directory 'app'.

ex:
from app.db_operations import create_db
"""

def create_app(config_name):
    """
    Application factory that returns a fully formed instance of the app

    The application context doesn't exist when this file is running, so 
    instead of being able to access values defined in the file config.py 
    the normal way as follows which uses the 'current_app' proxy:
    
    ~~~python
    from flask import current_app
    current_app.config['KEY_NAME']
    ~~~
    
    We have to manually access the config file as follows:

    ~~~python
    from config import config
    config[config_name].KEY_NAME
    ~~~
    
    Args:
      config_name (str): The name of the configuration to use
    
    """

    app = Flask(__name__, static_url_path="/static")
    print('This is the config name: {}'.format(config_name))
    
    # Select the desired config object from FLASK_ENV environment variable
    try:
      app.config.from_object(config[config_name])
      config[config_name].init_app(app)
    except Exception as e:
      print('')
      print('An error occurred initalizing the app. Be sure to set the environment')
      print('variables FLASK_ENV=(development|production) and FLASK_APP=myapp.py')
      print('')
      raise e

            
    db = sqlite3.connect(config[config_name].DB_NAME)
    cur = db.cursor()
  
    try:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY,
              user_facing_id VARCHAR(32),
              title TEXT,
              description TEXT,
              status INTEGER DEFAULT 0 -- 0: active, 1: disabled, 2: reserved for future use
            );
            CREATE TABLE IF NOT EXISTS assets(
                filename TEXT NOT NULL,
                create_date TEXT NOT NULL,
                aws_region TEXT NOT NULL,
                uploader_ip TEXT NOT NULL,
                event_id TEXT NOT NULL,
                size INT NOT NULL,
                etag TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES events(id)
            );
        """)
        db.commit()
        db.close()
    except Exception as e:
        print("Database creation error!")
        print(e)

    from app.landing import landing_bp
    app.register_blueprint(landing_bp)

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    return app
