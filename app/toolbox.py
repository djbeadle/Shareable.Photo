from flask import session, redirect
from functools import wraps
import json

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    print(json.dumps(dict(session)))
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/login')
    return f(*args, **kwargs)

  return decorated