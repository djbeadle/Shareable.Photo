from flask import Blueprint

manage_bp = Blueprint('manage_bp', __name__)

from app.manage import routes