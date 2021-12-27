from uuid import uuid4, UUID
from flask import render_template, request, current_app, Response
from db_operations import create_event, get_event_info, list_all_events
from app.landing import landing_bp

import json
from datetime import datetime

from s3 import generate_presigned_post

@landing_bp.route('/', methods=['GET'])
def home():
    text = 'This is the landing route!'
    return render_template('landing.html', content=text)

@landing_bp.route('/uploader/<user_facing_id>')
def upload(user_facing_id):
    return render_template(
        'uploader.html',
        user_facing_id=user_facing_id
    )

@landing_bp.route('/create_event')
def create_form():
    return render_template('create_event.html')


@landing_bp.route('/create_event', methods=['POST'])
def create_submit():
    new_event_user_facing_id = create_event(request.form['title'], request.form['description'])
    return render_template(
        'info.html',
        content=f'New event created with id {new_event_user_facing_id}. {get_event_info(new_event_user_facing_id)}.'
    )

@landing_bp.route('/events')
def list_events():
    return render_template(
        'list_events.html',
        events=list_all_events()
    )


@landing_bp.route('/get_event/<user_facing_id>', methods=['GET'])
def get_event(user_facing_id: str):
    return render_template(
        'info.html',
        content=f'{get_event_info(user_facing_id)}'
    )


@landing_bp.route('/<user_facing_id>/s3/params')
def get_presigned_s3_upload_url(user_facing_id):
    # TODO-prod: Keep tracing of the user_facing_ids and validate if this is in the database. For now just see if it's a valid UUID
    try:
        current_user_facing_id = UUID(user_facing_id)
    except ValueError as e:
        print(e)
        return Response({"error": "Now just hold on a minute, bucko."}, status=400, mimetype="application/json")

    params = request.args
    filename_with_folder = f'{user_facing_id}/{params["filename"]}'

    x = generate_presigned_post(filename_with_folder, params['type'])
    x['fields']['key'] = filename_with_folder
    return json.dumps(x)