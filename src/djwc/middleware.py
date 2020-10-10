import re

from django import apps
from django.conf import settings


class StaticMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.app = apps.apps.get_app_config('djwc')

    def __call__(self, request):
        response = self.get_response(request)

        if not getattr(response, 'content', ''):
            return response

        loaded = []
        for tag in re.findall(b'<([a-z]+-[-a-z]+)', response.content):
            if tag in loaded:
                continue

            if tag not in self.app.bcomponents:
                print(f'Element {tag} not found in registry')
                continue

            for script in self.app.bcomponents[tag]:
                src = script['src']
                if src in loaded:
                    continue
                module = script.get('module', True)
                response.content = response.content.replace(
                    b'</head>',
                    b''.join([
                        b'<script '
                        b'type="module"' if module else b'nomodule',
                        b' src="',
                        self.app.bstatic,
                        src,
                        b'">',
                        b'</script>',
                        b'</head>',
                    ])
                )
                loaded.append(src)
            loaded.append(tag)

        return response
