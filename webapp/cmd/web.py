from webapp.web import create_app, get_program_options

from livereload import Server

import pathlib
import socket


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    app = create_app()
    options = get_program_options()

    server = Server(app.wsgi_app)
    
    local_ip = get_local_ip()
    port = options.port
    
    print("\n" + "="*50)
    print("🚀 Server is running and accessible at:")
    print(f"   🏠 Local (This PC): http://localhost:{port}/")
    print(f"   🌐 Network (LAN):   http://{local_ip}:{port}/")
    print("="*50 + "\n")

    def ignore_node_modules(filepath):
        return "node_modules" in filepath or "tailwind" in filepath

    server.watch("webapp", ignore=ignore_node_modules)
    server.serve(
        debug=options.debug,
        host=options.host,
        port=int(options.port),
        restart_delay=2,
        # open_url_delay=7,
    )

    # app.run(host=options.host, port=int(options.port), debug=options.debug)
