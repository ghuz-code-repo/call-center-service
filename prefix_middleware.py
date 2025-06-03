class PrefixMiddleware:
    """
    Middleware for handling URL prefixes when an app is behind a reverse proxy.
    With improved debugging for static file requests.
    """
    def __init__(self, wsgi_app, app=None, prefix='/call-center'):
        self.wsgi_app = wsgi_app
        self.app = app
        self.prefix = prefix.rstrip('/')
        
        print(f"PrefixMiddleware initialized with prefix: '{self.prefix}'")
        
        if app is not None:
            app.config['APPLICATION_ROOT'] = self.prefix
            # We don't need to set static_url_path here
    
    def __call__(self, environ, start_response):
        script_name = environ.get('SCRIPT_NAME', '')
        path_info = environ.get('PATH_INFO', '')
        
        # Debug log every request
        print(f"Request: {path_info}")
        
        # Static file detection
        is_static = '/static/' in path_info
        if is_static:
            print(f"STATIC FILE REQUEST: {path_info}")
            
        # Handle requests to /call-center/...
        if path_info.startswith(self.prefix):
            environ['SCRIPT_NAME'] = script_name + self.prefix
            environ['PATH_INFO'] = path_info[len(self.prefix):] or '/'
            print(f"Rewritten path: {environ['PATH_INFO']}")
        
        # Special case for static files directly at /static
        elif path_info.startswith('/static/'):
            print(f"Direct static request detected: {path_info}")
            # Don't modify the path - Flask should handle it
            
        # Debug response
        def custom_start_response(status, headers, exc_info=None):
            print(f"Response: {status}")
            return start_response(status, headers, exc_info)
            
        return self.wsgi_app(environ, custom_start_response)
