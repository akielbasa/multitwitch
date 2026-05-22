from pyramid.response import Response
import jinja2

import simplejson as json

env = jinja2.Environment(loader=jinja2.FileSystemLoader('multitwitch/templates'))

def web(template=None, content_type='text/html', *args, **kwargs):
    """
    Decorator for web routes
    """
    def decorator(f):
        def wrapper(request):
            body = ''
            data = f(request)
            try:
                data["is_test"] = request.host.startswith("test.")
            except Exception:
                pass
            if template is not None:
                tmpl = env.get_template(template)
                body = tmpl.render(data)
            else:
                body = data
            return Response(
                body=body.encode('utf-8'),
                content_type=content_type,
                charset='utf-8',
            )
        return staticmethod(wrapper)
    return decorator

def ajax(*args, **kwargs):
    """
    Decorator for ajax routes

    Returns a response with a JSON version of the return value of f
    """
    def decorator(f):
        def wrapper(request):
            retval = f(request)
            return Response(
                body=json.dumps(retval).encode('utf-8'),
                content_type='application/json',
                charset='utf-8',
            )
        return staticmethod(wrapper)
    return decorator
