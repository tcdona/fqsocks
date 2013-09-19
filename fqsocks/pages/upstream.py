# -*- coding: utf-8 -*-
import httplib
import time
import logging
import os.path
from datetime import datetime
from .. import stat

import jinja2

from .. import httpd
from ..gateways import proxy_client


PROXIES_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'proxies.html')
UPSTREAM_HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'upstream.html')
LOGGER = logging.getLogger(__name__)
MAX_TIME_RANGE = 60 * 10


@httpd.http_handler('GET', 'upstream')
def upstream_page(environ, start_response):
    with open(UPSTREAM_HTML_FILE) as f:
        template = jinja2.Template(unicode(f.read(), 'utf8'))
    last_refresh_started_at = datetime.fromtimestamp(proxy_client.last_refresh_started_at)
    start_response(httplib.OK, [('Content-Type', 'text/html')])
    return template.render(
        _=environ['select_text'],
        last_refresh_started_at=last_refresh_started_at).encode('utf8')


@httpd.http_handler('POST', 'refresh-proxies')
def handle_refresh_proxies(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/plain')])
    proxy_client.auto_fix_enabled = True
    proxy_client.clear_proxy_states()
    proxy_client.refresh_proxies()
    return ['OK']


@httpd.http_handler('GET', 'proxies')
def handle_list_proxies(environ, start_response):
    start_response(httplib.OK, [('Content-Type', 'text/html')])
    proxies_counters = {}
    for counter in stat.counters:
        proxies_counters.setdefault(counter.proxy.public_name, []).append(counter)
    after = time.time() - MAX_TIME_RANGE
    proxies_stats = {}
    for proxy_public_name, proxy_counters in sorted(proxies_counters.items(),
                                                    key=lambda (proxy_public_name, proxy_counters): proxy_public_name):
        rx_bytes_list, rx_seconds_list, _ = zip(*[counter.total_rx(after) for counter in proxy_counters])
        rx_bytes = sum(rx_bytes_list)
        rx_seconds = sum(rx_seconds_list)
        if rx_seconds:
            rx_speed = rx_bytes / (rx_seconds * 1000)
        else:
            rx_speed = 0
        tx_bytes_list, tx_seconds_list, _ = zip(*[counter.total_tx(after) for counter in proxy_counters])
        tx_bytes = sum(tx_bytes_list)
        tx_seconds = sum(tx_seconds_list)
        if tx_seconds:
            tx_speed = tx_bytes / (tx_seconds * 1000)
        else:
            tx_speed = 0
        if not proxy_public_name:
            continue
        proxies_stats[proxy_public_name] = {
            'rx_speed_value': rx_speed,
            'rx_speed_label': '%05.2f KB/s' % rx_speed,
            'rx_bytes_value': rx_bytes,
            'rx_bytes_label': to_human_readable_size(rx_bytes),
            'tx_speed_value': tx_speed,
            'tx_speed_label': '%05.2f KB/s' % tx_speed,
            'tx_bytes_value': tx_bytes,
            'tx_bytes_label': to_human_readable_size(tx_bytes)
        }
    for proxy in proxy_client.proxies:
        proxy_public_name = proxy.public_name
        if not proxy_public_name:
            continue
        if proxy_public_name in proxies_stats:
            proxies_stats[proxy_public_name]['died'] = proxy.died
        else:
            proxies_stats[proxy_public_name] = {
                'died': proxy.died,
                'rx_speed_value': 0,
                'rx_speed_label': '00.00 KB/s',
                'rx_bytes_value': 0,
                'rx_bytes_label': '000.00 B',
                'tx_speed_value': 0,
                'tx_speed_label': '00.00 KB/s',
                'tx_bytes_value': 0,
                'tx_bytes_label': '000.00 B'
            }
    with open(PROXIES_HTML_FILE) as f:
        template = jinja2.Template(f.read())
    return template.render(proxies_stats=proxies_stats).encode('utf8')


def to_human_readable_size(num):
    for x in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return '%06.2f %s' % (num, x)
        num /= 1024.0

