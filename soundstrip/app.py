from .http_service import application_for, serve
from .exposure import exposure
from .exposure import compare
from .exposure import coverage
from .window import review as window_review
from .window import peak_window

PREFIX = 'soundstrip'
ROUTES = {'exposure': exposure, 'compare': compare, 'coverage': coverage,
          'window': window_review, 'peak': peak_window}
application = application_for(PREFIX, ROUTES)

if __name__ == "__main__":
    serve(application, 8824)
