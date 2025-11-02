from django.db import connection

class DBHealthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            connection.cursor()
        except Exception:
            connection.close()
        return self.get_response(request)
