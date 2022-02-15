import sqlite3, uuid, json
from flask import current_app, g
from typing import Union

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DB_NAME'])
    return db

def increment_view_counter(event_id, filename):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("UPDATE assets SET views = views + 1 WHERE filename=? AND event_id=?;", [filename, event_id])
        db.commit()
    except Exception as e:
        print(f'ERROR: Cannot update view counter, no file with filename "{filename}" and event_id "{event_id}" exists.')
        print(e)


def list_all_events():
    db = sqlite3.connect(current_app.config['DB_NAME'])
    cur = db.cursor()
  
    try:
        cur.execute("""
            SELECT user_facing_id, title, description, status, event_total
            FROM events
            LEFT JOIN (SELECT event_id, Sum(size) AS event_total FROM assets GROUP BY event_id) AS a
            ON events.user_facing_id = a.event_id""")
        rows = cur.fetchall()
        db.commit()
        db.close()
        return rows
    except Exception as e:
        print("An error occurred fetching all of the events.")
        print(e)


def list_users_events(owner_user_email):
    db = sqlite3.connect(current_app.config['DB_NAME'])
    cur = db.cursor()
  
    try:
        cur.execute(
            """
            SELECT  user_facing_id,
                    title,
                    description,
                    status,
                    event_total
            FROM events
            LEFT JOIN (SELECT event_id, Sum(size) AS event_total FROM assets GROUP BY event_id) AS a
            ON events.user_facing_id = a.event_id
            WHERE events.owner_user_id = ?
            """, [owner_user_email])
        
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
        cur.execute("SELECT user_facing_id, title, description, status, owner_user_id FROM events WHERE user_facing_id = ?;", (user_facing_id, ))
        return cur.fetchone()
    except Exception as e:
        print(f'An error occurred fetching event "{user_facing_id}"')


def create_event(title: str, description: str, creator_user_id: str, status=0):
    db = sqlite3.connect(current_app.config['DB_NAME'])
    cur = db.cursor()
  
    try:
        user_facing_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO events(user_facing_id, title, description, status, owner_user_id) VALUES (?, ?, ?, ?, ?);",
            [str(user_facing_id), title, description, status, creator_user_id]
        )

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


def get_user(user_id: str):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT user_id, email FROM users WHERE user_id = ?", [user_id])

        return cur.fetchone()
    except Exception as e:
        print(f'An error occurred while trying to retrieve user {user_id}.')
        print(e)


def insert_user(user_id, email):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO users (user_id, email) VALUES (?, ?);",
            [user_id, email]
        )
        db.commit()
    except Exception as e:
        print(f'An error occurred while trying to insert {user_id} into the users table.')
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

def get_image_thumbnails(event_id: str):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT filename, rowid FROM assets WHERE event_id = ? AND filename LIKE 'thumb%' order by create_date desc;", [event_id])
    return cur.fetchall()

def get_files_without_thumbnails(event_id: str):
    db = get_db()
    cur = db.cursor()
    cur.execute("select filename, event_id from assets where filename not like 'thumb%' AND event_id = ? AND 'thumb_'||filename not in (select filename from assets where event_id = ?);", [event_id, event_id])
    return cur.fetchall()

def get_next_asset_id(event_id: str):
    """
    Each file that is attempted to be uploaded is given a unique ID to ensure files with duplicate names do not overwrite each other.
    """
    db = get_db()
    cur = db.cursor()

    cur.execute("BEGIN;")
    cur.execute("UPDATE `events` SET `asset_id` = `asset_id`+1 WHERE `user_facing_id` = ?;", [event_id])
    cur.execute('SELECT `asset_id` - 1 FROM events WHERE `user_facing_id` = ?;', [event_id])
    x = cur.fetchone()
    cur.execute('COMMIT;')
    
    print(x)
    return x

def most_downloaded():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT filename, eventid, views FROM assets ORDER BY views DESC;")
    return cur.fetchall()