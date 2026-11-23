"""Print the production workflow result and verify the documented example."""
import argparse
from io import BytesIO
import json
import math
from pathlib import Path
from wsgiref.util import setup_testing_defaults


def request(app, path, data, method='POST'):
    content = json.dumps(data, ensure_ascii=False).encode('utf-8')
    env = {}
    setup_testing_defaults(env)
    env.update(PATH_INFO=path, REQUEST_METHOD=method, CONTENT_TYPE='application/json',
               CONTENT_LENGTH=str(len(content)), **{'wsgi.input': BytesIO(content)})
    status = []
    response = json.loads(b''.join(app(env, lambda code, _: status.append(int(code.split()[0])))))
    return status[0], response


def main(app, prefix, names):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=names)
    op = parser.parse_args().operation
    base = Path(__file__).resolve().parents[1] / 'examples'
    load = lambda ending: json.loads((base / (op + ending + '.json')).read_text(encoding='utf-8'))
    status, result = request(app, f'/{prefix}/{op}', load(''))
    if status != 200:
        raise RuntimeError((status, result))
    for route, expected in load('.checks'):
        value = result
        for field in route:
            value = value[field]
        same = math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12) if type(expected) is float else value == expected
        if not same:
            raise ValueError(f'{op} {route}: expected {expected}, got {value}')
    rejected, error = request(app, f'/{prefix}/{op}', load('.invalid'))
    if rejected != 400 or 'error' not in error:
        raise ValueError(f'{op} invalid case was not rejected: {rejected}, {error}')
    print(json.dumps({'result': result, 'invalid_case': error}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    from soundstrip.app import PREFIX, ROUTES, application
    main(application, PREFIX, ROUTES)
