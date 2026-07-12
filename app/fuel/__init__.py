from flask import Blueprint

fuel_bp = Blueprint('fuel', __name__, template_folder='../templates/fuel')

from app.fuel import routes
