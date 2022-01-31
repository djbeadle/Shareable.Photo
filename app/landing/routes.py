from flask import render_template, request, Response, session, redirect, url_for, current_app
from db_operations import create_event, get_event_info, list_users_events, event_asset_count, get_images, get_image_thumbnails
from app.landing import landing_bp
from app.toolbox import requires_auth

from s3 import create_presigned_url


@landing_bp.context_processor
def inject_user():
    """
    Always inject the user info if the user is signed in so we don't have to do it every time.

    https://stackoverflow.com/a/26498865
    """
    if session.get('profile'):
        return dict(user_info=session['profile'])
    else:
        return dict(user_info={})


@landing_bp.route('/')
def home():
    return render_template('landing.html')

@landing_bp.route('/uploader/<user_facing_id>')
def upload(user_facing_id):
    event_info = get_event_info(user_facing_id)
    return render_template(
        'uploader.html',
        user_facing_id=user_facing_id,
        custom_title=event_info[1],
        event_description=event_info[2]
    )

@landing_bp.route('/create_event')
@requires_auth
def create_form():
    return render_template('create_event.html')


@landing_bp.route('/create_event', methods=['POST'])
@requires_auth
def create_submit():
    new_event_user_facing_id = create_event(request.form['title'], request.form['description'], session['jwt_payload']['sub'])
    
    return redirect(f'{url_for("landing_bp.get_event", user_facing_id=new_event_user_facing_id)}')


@landing_bp.route('/events')
@requires_auth
def list_events():
    return render_template(
        'list_events.html',
        events=list_users_events(session['jwt_payload']['sub'])
    )


@landing_bp.route('/get_event/<user_facing_id>', methods=['GET'])
@requires_auth
def get_event(user_facing_id: str):
    current_user = session['jwt_payload']['sub']
    x = get_event_info(user_facing_id)
    # Warning: Admin can view all events!
    if x is None or (x[4] != current_user and current_user != current_app.config['ADMIN_ID']):
        return Response(f'Either this event does not exist or you are not authorized to view its gallery. Try logging in at {url_for("auth_bp.login", _external=True)}', status=404)

    event_images = [create_presigned_url(f'{user_facing_id}/{x[0]}') for x in list(get_images(user_facing_id))]
    
    return render_template(
        'info.html',
        asset_count=event_asset_count(user_facing_id),
        images=event_images,
        content=get_event_info(user_facing_id)
    )

@landing_bp.route('/gallery/<user_facing_id>', methods=['GET'])
def get_event_gallery(user_facing_id: str):
    x = get_event_info(user_facing_id)
    
    if x is None:
        return Response(f'Either this event does not exist or you are not authorized to view its gallery. Try logging in at {url_for("auth_bp.login", _external=True)}', status=404)

    event_images = [create_presigned_url(f'{user_facing_id}/{x[0]}') for x in list(get_image_thumbnails(user_facing_id))]
    
    return render_template(
        'gallery.html',
        asset_count=event_asset_count(user_facing_id),
        images=event_images,
        content=get_event_info(user_facing_id)
    )
