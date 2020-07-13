import importlib
from pathlib import Path

from django import apps
from django.conf import settings


class AppConfig(apps.AppConfig):
    name = 'djwc'
    verbose_name = 'Django WebComponents'

    def ready(self):
        DJWC = getattr(settings, 'DJWC', {})

        self.static = (Path(__file__).parent / 'static/djwc').absolute()
        self.bstatic = f'{settings.STATIC_URL}djwc/'.encode('utf8')

        self.components = dict()

        for name, config in apps.apps.app_configs.items():
            if 'polymer' in name:
                breakpoint()
            self.components.update(getattr(config, 'components', {}))

        for lib in DJWC.get('LIBRARIES', []):
            self.components.update(importlib.import_module(lib).components)

        if 'COMPONENTS' in DJWC:
            self.components.update(settings.DJWC['COMPONENTS'])

        self.bcomponents = {
            k.encode('utf8'): v for k, v in self.components.items()
        }
