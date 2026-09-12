import os
mode = os.getenv('FLASK_CONFIG') or 'production'
if mode != 'development':
    from gevent import monkey
    monkey.patch_all()

from app import app, socketio, config_name

if __name__ == '__main__':
    run_options = {}
    if config_name == 'development':
        run_options['use_reloader'] = False
        if socketio.async_mode == 'threading':
            # debugpy can provide non-terminal stdin for the local dev server.
            run_options['allow_unsafe_werkzeug'] = True
    socketio.run(app, port=app.config['FLASK_PORT'], host=app.config['FLASK_IP'],
                 **run_options)
