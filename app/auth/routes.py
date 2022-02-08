import http.client
from urllib.parse import urlencode
from flask import url_for, current_app, session, redirect, request, Response,render_template
from app.auth import auth_bp
from app.toolbox import requires_auth
from db_operations import get_user, insert_user, record_upload, get_next_asset_id

from s3 import generate_presigned_post

import json, urllib, hashlib
from uuid import UUID

@auth_bp.route('/dashboard')
def dashboard():
    return render_template(
        'dashboard.html',
        user_info=session['profile'],
        user_info_pretty=json.dumps(session['jwt_payload'], indent=4)
    )


@auth_bp.route('/login')
def login():
    return current_app.auth0.authorize_redirect(redirect_uri=url_for('.callback_handling', _external=True))


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

    return redirect('/dashboard')


@auth_bp.route('/profile', methods=['GET'])
@requires_auth
def profile():
    return render_template(
        'profile.html',
        user_info=session['profile'],
    )

@auth_bp.route('/profile', methods=['POST'])
@requires_auth
def set_profile():
    conn = http.client.HTTPSConnection("ceaseless-watcher.us.auth0.com")

    payload = json.dumps({
        "client_id": current_app.config["AUTH0_MANAGEMENT_ID"],
        "client_secret": current_app.config["AUTH0_MANAGEMENT_SECRET"],
        "audience": "https://ceaseless-watcher.us.auth0.com/api/v2/",
        "grant_type":"client_credentials"
    })
    headers = { 'content-type': "application/json" }

    conn.request("POST", "/oauth/token", payload, headers)

    res = conn.getresponse()
    data = res.read()
    auth0_resp = json.loads(data.decode("utf-8"))
    print(json.dumps(auth0_resp))

    print("*********")
    headers = {
            'Authorization': f'{auth0_resp["token_type"]} {auth0_resp["access_token"]}',
            'content-type': "application/json"
        }
    print(json.dumps(headers))
    print("*********")
    conn.request(
        "GET",
        f'/api/v2/users/{session["jwt_payload"]["sub"]}',
        headers=headers
    )
    
    data_2 = conn.getresponse().read()
    auth0_user_resp = json.loads(data_2.decode("utf-8"))

    # TODO singleton the token
    return json.dumps(auth0_user_resp)


@auth_bp.route('/logout')
@requires_auth
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('landing_bp.home', _external=True), 'client_id': current_app.config['AUTH0_CLIENT_ID']}
    return redirect(current_app.auth0.api_base_url + '/v2/logout?' + urlencode(params))



@auth_bp.route('/s3_upload_callback', methods = ['GET', 'POST', 'PUT'])
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


@auth_bp.route('/s3/upload_profile_pic')
@requires_auth
def upload_profile_pic():
    # https://github.com/transloadit/uppy/blob/main/packages/%40uppy/companion/src/server/controllers/s3.js
    try:
        print(f'metadata: {json.dumps(request.args)}')
        filename = request.args.get('type')
    except ValueError as e:
        print(e)
        return Response({"error": "Now just hold on a minute, bucko."}, status=400, mimetype="application/json")

    params = request.args
    # Using md5 here doesn't sit right with me but I'm not sure of a better solution. At least this way I'm not revealing
    # the user's Oauth sub publically and it should be hard enough to guess.
    filename_with_folder = f'profile_pic/{hashlib.md5(session["jwt_payload"]["sub"].encode("utf-8")).hexdigest()}{params["filename"].split(".")[1]}'

    x = generate_presigned_post(filename_with_folder, "", {})
    # x['fields']['content_type'] = file_type
    return json.dumps(x)


@auth_bp.route('/<user_facing_id>/s3/upload_thumbnail')
def get_presigned_s3_thumbnail_url(user_facing_id):
    print(json.dumps(request.args, indent=2))
    return json.dumps(generate_presigned_post(f'{user_facing_id}/{request.args["filename"]}', "", {}))


@auth_bp.route('/<user_facing_id>/s3/params')
def get_presigned_s3_upload_url(user_facing_id):
    # https://github.com/transloadit/uppy/blob/main/packages/%40uppy/companion/src/server/controllers/s3.js
    # TODO-prod: Keep tracing of the user_facing_ids and validate if this is in the database. For now just see if it's a valid UUID
    try:
        current_user_facing_id = UUID(user_facing_id)
        print(f'metadata: {json.dumps(request.args)}')
        uploader_name = request.args.get('metadata[uploader-name]')
        file_type = request.args.get('type')
    except ValueError as e:
        print(e)
        return Response({"error": "Now just hold on a minute, bucko."}, status=400, mimetype="application/json")

    params = request.args
    # Due to issues with how S3 encodes plus signs I'm just going to replace them with spaces for now.
    filename_with_folder = f'{user_facing_id}/{get_next_asset_id(user_facing_id)[0]}_{uploader_name.replace(" ", "-")}_{params["filename"].replace("+", " ")}'
    
    fields = {
        'x-amz-meta-uploader-name': uploader_name,
        'Content-Type': file_type
    }

    x = generate_presigned_post(filename_with_folder, params['type'], fields)
    # x['fields']['content_type'] = file_type
    return json.dumps(x)
