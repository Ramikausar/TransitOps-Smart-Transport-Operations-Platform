from flask import Blueprint

expenses_bp = Blueprint('expenses', __name__, template_folder='../templates/expenses')

from app.expenses import routes
