"""Bounded, loopback-only service for offline data processing."""
import argparse
import json
import math
from wsgiref.simple_server import make_server

MAX_BODY = 512 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON member: {key}')
        result[key] = value
    return result


def no_constant(value):
    raise ValueError(f'non-finite JSON constant: {value}')


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('JSON number out of range')
    return number


def application_for(prefix, routes):
    def application(env, start_response):
        path, method = env['PATH_INFO'], env['REQUEST_METHOD']
        status = '200 OK'
        if method == 'GET' and path == '/health':
            result = {'service': prefix, 'operations': sorted(routes)}
        elif not path.startswith('/' + prefix + '/') or path.rsplit('/', 1)[0] != '/' + prefix or path.rsplit('/', 1)[-1] not in routes:
            status, result = '404 Not Found', {'error': 'unknown operation'}
        elif method != 'POST':
            status, result = '405 Method Not Allowed', {'error': 'use POST'}
        elif env.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
            status, result = '415 Unsupported Media Type', {'error': 'use application/json'}
        else:
            try:
                size = int(env.get('CONTENT_LENGTH') or '0')
                if size > MAX_BODY:
                    status, result = '413 Payload Too Large', {'error': 'request exceeds limit'}
                else:
                    if size <= 0:
                        raise ValueError('nonempty JSON required')
                    payload = env['wsgi.input'].read(size)
                    if len(payload) != size:
                        raise ValueError('truncated request')
                    data = json.loads(payload.decode('utf-8'), object_pairs_hook=unique_object,
                                      parse_constant=no_constant, parse_float=finite_float)
                    if type(data) is not dict:
                        raise ValueError('request must be a JSON object')
                    result = routes[path.rsplit('/', 1)[-1]](data)
            except (ValueError, KeyError, TypeError, RecursionError, OverflowError) as exc:
                status, result = '400 Bad Request', {'error': str(exc)}
        body = json.dumps(result, allow_nan=False, ensure_ascii=True).encode('utf-8')
        headers = [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(body)))]
        if status.startswith('405'):
            headers.append(('Allow', 'POST'))
        start_response(status, headers)
        return [body]
    return application


def serve(application, port):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=port)
    args = parser.parse_args()
    with make_server('127.0.0.1', args.port, application) as server:
        print(f'Listening on http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()
