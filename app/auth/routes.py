import json
from urllib.parse import urlencode
from flask import url_for, current_app, session, redirect, render_template
from app.auth import auth_bp
from app.toolbox import requires_auth
from db_operations import get_user, insert_user


@auth_bp.route('/dashboard')
@requires_auth
def dashboard():
    return render_template(
        'dashboard.html',
        user_info=session['profile'],
        user_info_pretty=json.dumps(session['jwt_payload'], indent=4)
    )


@auth_bp.route('/login')
def login():
    return current_app.auth0.authorize_redirect(redirect_uri='http://localhost:5000/authy_callback')


# Here we're using the /callback route.
@auth_bp.route('/authy_callback')
def callback_handling():
    # Handles response from token endpoint
    current_app.auth0.authorize_access_token()
    resp = current_app.auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    if not get_user(userinfo['sub']):
        insert_user(userinfo['sub'], userinfo['email'])

    return redirect('/events')


@auth_bp.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('landing_bp.home', _external=True), 'client_id': 'TRuQsy4uFa27xxcuEDZDnxvFEWlwctPb'}
    return redirect(current_app.auth0.api_base_url + '/v2/logout?' + urlencode(params))