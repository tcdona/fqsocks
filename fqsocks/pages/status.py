import httplib
import os

import jinja2

from .. import httpd

STATUS_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'status.html')


@httpd.http_handler('GET', '')
def status_page(environ, start_response):
    with open(STATUS_HTML_FILE) as f:
        template = jinja2.Template(unicode(f.read(), 'utf8'))
    start_response(httplib.OK, [('Content-Type', 'text/html')])
    return [template.render(_=environ['select_text']).encode('utf8')]
