import re

from django import apps
from django.conf import settings


class ScriptMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.app = apps.apps.get_app_config('djwc')

    def __call__(self, request):
        response = self.get_response(request)

        if not getattr(response, 'content', ''):
            return response

        loaded = []
        for tag in re.findall(b'</(?P<t>[a-z]*-[a-z]*)>', response.content):
            if tag in loaded:
                continue

            if tag not in self.app.bcomponents:
                print(f'Element {tag} not found in registry')
                continue

            response.content = response.content.replace(
                b'</head>',
                b''.join([
                    b'<script type="module">import ',
                    b"'",
                    self.app.bstatic,
                    self.app.bcomponents[tag].encode('utf8'),
                    b"'",
                    b'</script>',
                    b'</head>',
                ])
            )
            loaded.append(tag)

        return response
