from . import networking
import logging
import random
import sys
import gevent

LOGGER = logging.getLogger(__name__)

sub_map = {}
sub_lock = set()

def substitute_ip(client, dst_black_list):
    if client.dst_ip not in sub_map:
        gevent.spawn(fill_sub_map, client.host, client.dst_ip)
        return False
    if client.dst_ip in sub_map and sub_map[client.dst_ip] is None:
        return False
    candidate_ips = []
    for ip in sub_map.get(client.dst_ip):
        if (ip, client.dst_port) not in dst_black_list:
            candidate_ips.append(ip)
    if candidate_ips:
        substituted_ip = random.choice(candidate_ips)
        LOGGER.info('[%s] substitute ip: %s %s => %s' % (client, client.host, client.dst_ip, substituted_ip))
        client.dst_ip = substituted_ip
        return True
    return False


def fill_sub_map(host, dst_ip):
    if host in sub_lock:
        return
    sub_lock.add(host)
    try:
        sub_host = '%s.sub.f-q.co' % '.'.join(reversed(dst_ip.split('.')))
        ips = networking.resolve_ips(sub_host)
        if host:
            ips += networking.resolve_ips(host)
        if dst_ip in ips:
            ips.remove(dst_ip)
        if ips:
            sub_map[dst_ip] = ips
        else:
            sub_map[dst_ip] = None
    except:
        LOGGER.error('failed to fill host map due to %s' % sys.exc_info()[1])
    finally:
        sub_lock.remove(host)
