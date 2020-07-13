import asyncio
from pathlib import Path
import os
import re
from urllib import request

from django import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Download registered webcomponents'
    downloading = []

    def handle(self, *args, **kwargs):
        self.djwc = apps.apps.get_app_config('djwc')

        async def downloads():
            return await asyncio.gather(*[
                self.download(source)
                for tagname, source in self.djwc.components.items()
            ])

        asyncio.run(downloads())

    async def download(self, source):
        target = self.djwc.static / source

        if target.exists():
            return

        print('+ ' + source)

        if not target.parent.exists():
            os.makedirs(target.parent)

        url = 'https://unpkg.com/' + source
        tries = 10
        while tries:
            try:
                filename, headers = request.urlretrieve(url, filename=target)
            except Exception as e:
                tries -= 1
                if not tries:
                    raise
                print(e)
            else:
                break

        with open(target, 'r') as f:
            contents = f.read()

        results = set([
            i[1]
            for i in re.findall(
                r"""(import|from)\s['"]([^'"]*)['"]""",
                contents,
            )
        ])
        downloads = []
        for module in results:
            # convert relative paths to absolute paths
            if module.startswith('.'):
                module = '/'.join(source.split('/')[:-1]) + '/' + module

            # /./ not needed in a path
            module = module.replace('/./', '/')

            # cancel out /.. in paths
            while '/..' in module:
                module = re.sub('/[^/]*/\.\.', '', module)

            # prevent recursion
            if module in downloads:
                continue

            # download OAOO
            if module not in self.downloading:
                self.downloading.append(module)
                downloads.append(self.download(module))

            contents = re.sub(
                module,
                f'{settings.STATIC_URL}djwc/{module}',
                contents,
            )

        with open(target, 'w+') as f:
            f.write(contents)

        await asyncio.gather(*downloads)
