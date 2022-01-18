from uuid import UUID
from flask import render_template, request, Response, session, redirect, url_for, current_app
from db_operations import create_event, get_event_info, list_users_events, record_upload, event_asset_count, get_images
from app.landing import landing_bp
from app.toolbox import requires_auth


import json, urllib
from datetime import datetime


from s3 import generate_presigned_post, create_presigned_url


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


@landing_bp.route('/s3_upload_callback', methods = ['GET', 'POST', 'PUT'])
def sns():
    # TODO-Daniel: Verify Signature from Amazon to prevent malicious
    """
       [
            {
                "eventVersion" : "2.1",
                "eventSource" : "aws:s3",
                "awsRegion" : "us-east-1",
                "eventTime" : "2022-01-12T18:13:40.260Z",
                "eventName" : "ObjectCreated:Post",
                "userIdentity" : {
                    "principalId" : "AWS:AIDAUZYMYSEH2T565DTFL"
                },
                "requestParameters" : {
                     "sourceIPAddress" : "151.205.187.56"
                },
                "responseElements" : {
                    "x-amz-request-id" : "Q632NM5SXJZE1DZY",
                    "x-amz-id-2" : "ygP97z1gE22xNh57jCt6ypnlEMi8Ab3PbiwAh+wO9TKQpCDCRdLk1et/7+C3L4vphMxV8Pr9rRwUuWP0BG1Nrq/NYPmyRjFy"
                },
                "s3" : {
                    "s3SchemaVersion" : "1.0",
                    "configurationId" : "Eventfire Upload",
                    "bucket" : {
                        "name" : "eventfire",
                        "ownerIdentity" : {
                        "principalId" : "A1N3DD51J9UNG7"
                        },
                        "arn" : "arn:aws:s3:::eventfire"
                    },
                    "object" : {
                        "key" : "96bf309f-e2db-4910-8e74-96580a2e0c4b/IMG_2605.jpeg",
                        "size" : 480277,
                        "eTag" : "47486c8fe6dc435934dfd323da7beaa5",
                        "sequencer" : "0061DF1A541D57A6A0"
                    }
                }
            }
        ]
    """
    # AWS sends JSON with text/plain mimetype
    # TODO calculate e-tags client side and prevent duplicate uploads https://teppen.io/2018/06/23/aws_s3_etags/#what-is-an-s3-etag
    try:
        js = json.loads(request.data)
    except:
        pass

    hdr = request.headers.get('X-Amz-Sns-Message-Type')
    # subscribe to the SNS topic
    if hdr == 'SubscriptionConfirmation' and 'SubscribeURL' in js:
        # r = requests.get(js['SubscribeURL'])
        with urllib.request.urlopen(js['SubscribeURL']) as f:
            print(f.read().decode('utf-8'))

    # if hdr == 'Notification':
    #    print(js['Message'], js['Timestamp'])

    msg = js['Message']
    for r in json.loads(msg)['Records']:
        # print(json.dumps(r, indent=2))
        folder, filename = r['s3']['object']['key'].split('/')
        record_upload(
            filename,
            folder,
            r['eventTime'],
            r['awsRegion'],
            r['requestParameters']['sourceIPAddress'],
            r['s3']['object']['size'],
            r['s3']['object']['eTag'],
        )

    return 'OK\n'


@landing_bp.route('/<user_facing_id>/s3/params')
def get_presigned_s3_upload_url(user_facing_id):
    # TODO-prod: Keep tracing of the user_facing_ids and validate if this is in the database. For now just see if it's a valid UUID
    try:
        current_user_facing_id = UUID(user_facing_id)
    except ValueError as e:
        print(e)
        return Response({"error": "Now just hold on a minute, bucko."}, status=400, mimetype="application/json")

    params = request.args
    # Due to issues with how S3 encodes plus signs I'm just going to replace them with spaces for now.
    filename_with_folder = f'{user_facing_id}/{params["filename"].replace("+", " ")}'

    x = generate_presigned_post(filename_with_folder, params['type'])
    x['fields']['key'] = filename_with_folder
    return json.dumps(x)
