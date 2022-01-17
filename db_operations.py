import sqlite3, uuid, json
from flask import current_app, g


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DB_NAME'])
    return db


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
        return cur.fetchone()
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


def record_upload(filename, eventName, eventTime, awsRegion, sourceIp,  size, etag):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO assets(filename, create_date, aws_region, uploader_ip, event_id, size, etag) values (?,?,?,?,?,?,?);",
            [filename, eventTime, awsRegion, sourceIp, eventName, size, etag]
        )
        db.commit()
    except Exception as e:
        print(f'An error occurred while trying to insert {filename} into the assets table.')
        print(e)


def event_asset_count(event_id: str):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT count(filename) FROM assets WHERE event_id=?;", [event_id])
    return cur.fetchone()[0]


def get_images(event_id: str):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT filename FROM assets WHERE event_id = ?", [event_id])
    return cur.fetchall()