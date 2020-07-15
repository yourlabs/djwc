import asyncio
import json
from pathlib import Path
import os
import re
import shlex
from urllib import request

from django import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import httpx


class Command(BaseCommand):
    help = 'Download registered webcomponents'
    downloading = []

    def handle(self, *args, **kwargs):
        asyncio.run(self.async_handle(*args, **kwargs))

    async def async_handle(self, *args, **kwargs):
        self.djwc = apps.apps.get_app_config('djwc')
        modules = await self.get_modules(self.djwc.components.values())
        while modules:
            modules = await self.install([*modules.values()])

    async def install(self, modules):
        urls = {}
        for module in modules:
            latest = module['dist-tags']['latest']
            url = module['versions'][latest]['dist']['tarball']
            urls[module['name']] = url

        async def install_tgz(modname, url):
            target = self.djwc.static / modname
            if not target.exists():
                os.makedirs(target)

            if not os.path.exists(os.path.join(target, url.split('/')[-1])):
                temp = self.djwc.static / url.split('/')[-1]
                cmd = ' && '.join([
                    shlex.join(['cd', str(target)]),
                    shlex.join(['wget', url]),
                    shlex.join(['tar', 'xvzf', url.split('/')[-1], '--strip=1']),
                    shlex.join(['rm', '-rf', url.split('/')[-1]]),
                ])
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                print(f'[{cmd!r} exited with {proc.returncode}]')

            with open(os.path.join(target, 'package.json'), 'r') as f:
                package = f.read()
            return json.loads(package)

        results = await asyncio.gather(*[
            install_tgz(modname, url) for modname, url in urls.items()
        ])
        dependencies = dict()
        for result in results:
            dependencies.update(result.get('dependencies', {}))

        if dependencies:
            return dependencies

    async def get_modules(self, sources):
        results = []
        for source in sources:
            parts = source.split('/')
            async with httpx.AsyncClient() as client:
                while parts:
                    results.append(client.get(
                         f'https://registry.npmjs.org/{"/".join(parts)}/'
                    ))
                    parts.pop()
        return {
            res.json()['name']: res.json()
            for res in await asyncio.gather(*results)
            if res.status_code == 200
        }

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
