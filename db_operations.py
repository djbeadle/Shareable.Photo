import sqlite3, uuid, json
from flask import current_app

def list_all_events():
    db = sqlite3.connect(current_app.config['DB_NAME'])
    cur = db.cursor()
  
    try:
        cur.execute("SELECT user_facing_id, title, description, status FROM events;")
        rows = cur.fetchall()
        db.commit()
        db.close()
        return rows
    except Exception as e:
        print("An error occurred fetching all of the events.")
        print(e)
    

def get_event_info(user_facing_id):
    db = sqlite3.connect(current_app.config['DB_NAME'])
    cur = db.cursor()

    try:
        cur.execute("SELECT user_facing_id, title, description, status FROM events WHERE user_facing_id = ?;", (user_facing_id, ))
        return json.dumps(cur.fetchone())
    except Exception as e:
        print(f'An error occurred fetching event "{user_facing_id}"')

def create_event(title: str, description: str, status=0):
    db = sqlite3.connect(current_app.config['DB_NAME'])
    cur = db.cursor()
  
    try:
        user_facing_id = uuid.uuid4()
        cur.execute("INSERT INTO events(user_facing_id, title, description, status) values (?, ?, ?, ?);", (str(user_facing_id), title, description, status))

        db.commit()
        db.close()

        return user_facing_id
    except Exception as e:
        print(f'An error occurred while trying to insert event "{title}" in to "{ current_app.config["DB_NAME"] }".')
        print(e)