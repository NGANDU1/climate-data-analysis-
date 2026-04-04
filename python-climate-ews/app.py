from flask import Flask, jsonify, send_from_directory, redirect
from flask_cors import CORS
from config import config
from models import db, init_db
import os

def create_app(config_name=None):
    """Application factory for creating Flask app"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Disable Flask's built-in static handler because it conflicts with our catch-all routes.
    # We serve the public UI from `../frontend` and shared assets from `../assets`.
    frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    app = Flask(
        __name__,
        static_folder=frontend_folder,
        static_url_path=None,
    )

    admin_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'admin'))
    assets_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app)
    init_db(app)
    
    # Import and register blueprints
    from routes import (
        weather_routes,
        risk_routes,
        alert_routes,
        user_routes,
        admin_routes,
        auth_routes,
        dataset_routes,
        weather_admin_routes,
        model_routes,
        report_routes,
        forecast_routes,
        monitoring_routes,
        source_routes,
    )
    
    app.register_blueprint(weather_routes.api, url_prefix='/api')
    app.register_blueprint(risk_routes.api, url_prefix='/api/risk')
    app.register_blueprint(alert_routes.api, url_prefix='/api/alerts')
    app.register_blueprint(user_routes.api, url_prefix='/api/users')
    app.register_blueprint(admin_routes.api, url_prefix='/api/admin')
    app.register_blueprint(auth_routes.api, url_prefix='/api/auth')
    app.register_blueprint(dataset_routes.api, url_prefix='/api/admin/datasets')
    app.register_blueprint(weather_admin_routes.api, url_prefix='/api/admin/weather-data')
    app.register_blueprint(model_routes.api, url_prefix='/api/admin/models')
    app.register_blueprint(report_routes.api, url_prefix='/api/admin/reports')
    app.register_blueprint(monitoring_routes.api, url_prefix='/api/admin/monitoring')
    app.register_blueprint(source_routes.api, url_prefix='/api/admin/sources')
    app.register_blueprint(forecast_routes.api, url_prefix='/api/predictions')

    # Background open-data sync (runs best-effort every minute; only executes when due)
    try:
        from services.external_sync_scheduler import start_external_sync_scheduler

        start_external_sync_scheduler(app)
    except Exception:
        # Don't block app startup if scheduler fails
        pass
    
    # Serve frontend files
    @app.route('/')
    def serve_home():
        return send_from_directory(app.static_folder, 'home.html')

    # Block public access to legacy template pages that should not be user-accessible.
    @app.route('/users.html')
    def block_public_users_page():
        return redirect('/', code=302)

    # Public dashboard (old default landing)
    @app.route('/dashboard')
    @app.route('/dashboard/')
    def serve_dashboard():
        return send_from_directory(app.static_folder, 'index.html')

    # Serve admin panel from the legacy /admin folder (not under the main static folder).
    @app.route('/admin/')
    @app.route('/admin/<path:path>')
    def serve_admin(path='index.html'):
        if os.path.exists(os.path.join(admin_folder, path)):
            return send_from_directory(admin_folder, path)
        return send_from_directory(admin_folder, 'index.html')

    # Serve shared assets (themes, JS helpers, images).
    @app.route('/assets/<path:path>')
    def serve_assets(path):
        if os.path.exists(os.path.join(assets_folder, path)):
            return send_from_directory(assets_folder, path)
        return jsonify({'error': 'Not found'}), 404

    # Some deployments may include the folder name in the URL.
    @app.route('/frontend/')
    @app.route('/frontend/<path:path>')
    def serve_public_prefixed(path='home.html'):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'home.html')

    # Legacy compatibility: redirect old template folder URLs to /frontend/.
    @app.route('/templatemo_607_glass_admin/')
    @app.route('/templatemo_607_glass_admin/<path:path>')
    def redirect_legacy_template_path(path=''):
        target = f"/frontend/{path}" if path else "/frontend/"
        return redirect(target, code=301)
    
    @app.route('/<path:path>')
    def serve_static(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'home.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
