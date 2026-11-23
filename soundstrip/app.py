from .http_service import application_for, serve
from .exposure import exposure
from .exposure import compare
from .exposure import coverage

PREFIX = 'soundstrip'
ROUTES = {'exposure': exposure, 'compare': compare, 'coverage': coverage}
application = application_for(PREFIX, ROUTES)

if __name__ == "__main__":
    serve(application, 8824)
