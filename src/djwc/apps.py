import copy
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
            self.components.update(getattr(config, 'components', {}))

        for lib in DJWC.get('LIBRARIES', []):
            self.components.update(importlib.import_module(lib).components)

        if 'COMPONENTS' in DJWC:
            self.components.update(settings.DJWC['COMPONENTS'])

        for tag, definitions in self.components.items():
            if not isinstance(definitions, (list, tuple)):
                definitions = (definitions,)

            self.components[tag] = tuple(
                definition
                if isinstance(definition, dict)
                else dict(src=definition)
                for definition in definitions
            )

        self.bcomponents = {
            tag.encode('utf8'): definitions
            for tag, definitions in copy.deepcopy(self.components).items()
        }
        for tag, definition in self.bcomponents.items():
            for i in range(0, len(self.bcomponents[tag])):
                self.bcomponents[tag][i]['src'] = \
                    self.bcomponents[tag][i]['src'].encode('utf8')
