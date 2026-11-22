"""Flask uygulamasının giriş noktası ve uygulama fabrikası."""

from flask import Flask, render_template, g, request
import sqlite3

from config import Config


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    from security import RecordIDConverter
    app.url_map.converters['int'] = RecordIDConverter
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)

    from database import init_app
    init_app(app)
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from security import csrf_token, protect_csrf
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    from routes.books import bp as books_bp
    app.register_blueprint(books_bp)
    from routes.google_books import bp as google_books_bp
    app.register_blueprint(google_books_bp)
    from routes.loans import bp as loans_bp
    app.register_blueprint(loans_bp)
    from routes.reservations import bp as reservations_bp
    from routes.notifications import bp as notifications_bp
    app.register_blueprint(reservations_bp)
    app.register_blueprint(notifications_bp)
    from routes.members import bp as members_bp
    from routes.settings import bp as settings_bp
    app.register_blueprint(members_bp)
    app.register_blueprint(settings_bp)
    from routes.design_patterns import bp as design_patterns_bp
    app.register_blueprint(design_patterns_bp)
    from routes.digital import bp as digital_bp
    from services.digital_service import MEDIA_LIMIT
    app.register_blueprint(digital_bp)
    from routes.member_portal import bp as member_portal_bp
    from routes.categories import bp as categories_bp
    app.register_blueprint(member_portal_bp)
    app.register_blueprint(categories_bp)
    from routes.member_cards import bp as member_cards_bp
    app.register_blueprint(member_cards_bp)
    from routes.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp)
    from routes.reports import bp as reports_bp
    app.register_blueprint(reports_bp)
    from routes.system import bp as system_bp
    app.register_blueprint(system_bp)

    @app.before_request
    def digital_upload_limit():
        if (request.endpoint in ('books.add', 'books.edit') and request.mimetype == 'multipart/form-data'
                and g.user and g.user.role == 'admin'):
            request.max_content_length = MEDIA_LIMIT + 256 * 1024

    app.before_request(protect_csrf)
    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.context_processor
    def notification_badge():
        from services.notification_service import unread_count
        return {'unread_notifications':unread_count(g.user.id) if getattr(g,'user',None) and not getattr(g,'database_unavailable',False) else 0}

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    @app.errorhandler(422)
    @app.errorhandler(500)
    def error_page(error):
        return render_template('error.html', code=error.code), error.code

    @app.errorhandler(sqlite3.DatabaseError)
    def database_error(error):
        # Hata sayfası tekrar sorgu çalıştırıp aynı veritabanı hatasına düşmez.
        g.database_unavailable = True
        g.user = None
        app.logger.warning('Veritabanı işlemi tamamlanamadı: %s',type(error).__name__)
        return render_template('error.html',code=503),503

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=()'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; img-src 'self' https://books.google.com https://books.googleusercontent.com https://covers.openlibrary.org; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        if response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/')
    def index():
        return render_template('dashboard.html')

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000)
