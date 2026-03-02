from webapp.web import create_app, get_program_options

from livereload import Server

import pathlib


def main():
    app = create_app()
    options = get_program_options()

    server = Server(app.wsgi_app)
    print(pathlib.Path(__file__).parent)
    server.watch("webapp")
    server.serve(
        debug=options.debug,
        host=options.host,
        port=int(options.port),
        restart_delay=2,
        # open_url_delay=7,
    )

    # app.run(host=options.host, port=int(options.port), debug=options.debug)
