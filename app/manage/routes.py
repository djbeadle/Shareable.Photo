from http.client import HTTPResponse
from flask import session, render_template, Response
from app.manage import manage_bp

from db_operations import list_all_events, list_all_users

import json

@manage_bp.context_processor
def inject_user():
    """
    Always inject the user info if the user is signed in so we don't have to do it every time.

    https://stackoverflow.com/a/26498865
    """
    if session.get('profile'):
        return dict(user_info=session['profile'])
    else:
        return dict(user_info={})


@manage_bp.before_request
def djbeadle_only():
    if session.get('jwt_payload') is None or session['jwt_payload']['sub'] != 'google-oauth2|102945930198047778272':
        return Response(json.dumps({"error": "Sorry, buddy."}), status=400, mimetype="application/json")

@manage_bp.route("/manage/all_events")
def list_events():
    return render_template(
        'list_events.html',
        events=list_all_events()
    )

@manage_bp.route("/manage/all_users")
def list_users():
    return render_template(
        'list_users.html',
        users=list_all_users()
    )