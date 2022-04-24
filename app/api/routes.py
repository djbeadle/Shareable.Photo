from flask import jsonify
from importlib_metadata import requires
from db_operations import get_images, get_image_thumbnails
from app.toolbox import requires_auth
from app.api import api_bp

from s3 import create_presigned_url


@api_bp.context_processor
def inject_user():
    """
    Always inject the user info if the user is signed in so we don't have to do it every time.

    https://stackoverflow.com/a/26498865
    """
    if session.get('profile'):
        return dict(user_info=session['profile'])
    else:
        return dict(user_info={})


@api_bp.route('/api/thumbs')
@requires_auth
def home():
    user_facing_id = "6e434cd2-f645-4864-afac-eff217cf0cee"
    
    return jsonify(
        # [("presigned thumbnail url", "url to get presigned full resolution url", rowid)][
        thumbs=[(
            create_presigned_url(f'{user_facing_id}/{x[0]}', disposition="inline"),
            f'{user_facing_id}/{x[0].replace("thumb_", "", 1)}',
            x[1]
        ) for x in list(get_image_thumbnails(user_facing_id))]
    )
