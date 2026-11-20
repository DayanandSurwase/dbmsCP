import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

from routes.dashboard import dashboard_bp
from routes.accounts import accounts_bp
from routes.contracts import contracts_bp
from routes.transactions import transactions_bp

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret')

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(contracts_bp)
app.register_blueprint(transactions_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def not_found(e):
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
def server_error(e):
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug, port=5000)
