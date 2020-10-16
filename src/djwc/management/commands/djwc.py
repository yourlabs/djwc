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

import logging
from async_task_queue import AsyncTask, AsyncTaskQueue


class Command(BaseCommand):
    help = 'Download registered webcomponents'

    def handle(self, *args, **kwargs):
        asyncio.run(self.async_handle(*args, **kwargs))

    async def async_handle(self, *args, **kwargs):
        self.djwc = apps.apps.get_app_config('djwc')
        self.modules = dict()

        logger = logging.getLogger("foo")
        self.task_queue = AsyncTaskQueue(
            logger,
            batch_size=12,
            execution_timeout=300
        )
        self.task_queue.enqueue([
            AsyncTask(self.script_install, script)
            for t in self.djwc.components.values()
            for d in t
            for script in d.values()
        ])
        print(f'Ensuring all dependencies extracted in {self.djwc.static} ...')
        await self.task_queue.execute()

        self.patches = []
        self.task_queue = AsyncTaskQueue(
            logger,
            batch_size=60,
            execution_timeout=300
        )
        self.task_queue.enqueue([
            AsyncTask(self.script_patch, script)
            for t in self.djwc.components.values()
            for d in t
            for script in d.values()
        ])
        print(f'Ensuring all scripts have patched imports ...')
        await self.task_queue.execute()

    def resolve(self, target, parent=None):
        print('RESOLVE ', target, parent)
        if str(target).startswith('.'):
            # resolve based on parent module
            return self.resolve((self.djwc.static / parent / '..' / target).resolve())

        target = self.djwc.static / target

        if target.is_dir():
            # resolve directory from package.json
            pkg = target / 'package.json'
            if pkg.exists():
                with open(pkg, 'r') as f:
                    pkg = json.loads(f.read())
                if 'module' in pkg:
                    filename = pkg['module']
                elif 'main' in pkg:
                    filename = pkg['main']
                else:
                    filename = 'index.js'
            return target / filename

        elif not str(target).endswith('.js'):
            # append .js on filenames
            js = Path(str(target) + '.js')
            if js.exists:
                return js

        return target

    async def script_patch(self, script, parent=None):
        if script in self.patches:
            return
        self.patches.append(script)
        target = self.resolve(script, parent)
        print('MODULE ', script)
        print('PATCH ', target)

        with open(target, 'r') as f:
            contents = f.read()

        results = {
            i[2]: i[1]
            for i in re.findall(
                r"""(import|from)\s(['"])([^'"]*)['"]""",
                contents,
            )
        }
        for dependency, quote in results.items():
            if dependency.startswith(settings.STATIC_URL):
                dependency = dependency.replace(
                    f'{settings.STATIC_URL}djwc/',
                    '',
                )
                self.task_queue.enqueue([
                    AsyncTask(
                        self.script_patch,
                        dependency,
                        script,
                    )
                ])
                continue

            new_path = self.resolve(dependency, script)
            new_imp = str(new_path)[len(str(self.djwc.static) + '/'):]
            new_url = f'{settings.STATIC_URL}djwc/{new_imp}'
            print('DEPENDENCY ' + dependency)
            print('PATH ' + str(new_path))
            print('IMP ' + new_imp)
            print('URL ' + new_url)
            if script.startswith('.'):
                breakpoint()
                new_path = self.resolve(dependency, script)
            contents = contents.replace(
                quote + dependency + quote,
                quote + new_url + quote,
            )

            self.task_queue.enqueue([AsyncTask(
                self.script_patch,
                new_imp,
                script,
            )])

        with open(target, 'w') as f:
            f.write(contents)

    async def script_install(self, name):
        parts = name.split('/')
        if name.endswith('.js'):
            parts = parts[:-1]

        tests = []
        async with httpx.AsyncClient() as client:
            while parts:
                tests.append(client.get(
                     f'https://registry.npmjs.org/{"/".join(parts)}/'
                ))
                parts.pop()
        results = await asyncio.gather(*tests)
        for result in results:
            if result.status_code == 200:
                break
        if not result.status_code:
            print('Could not figure module for ' + name)
            return

        module = result.json()
        if 'name' not in module:
            import sys
            print('NPM module not found', name)
            sys.exit(1)
        if module['name'] in self.modules:
            return
        self.modules[module['name']] = module

        latest = module['dist-tags']['latest']
        url = module['versions'][latest]['dist']['tarball']

        target = self.djwc.static / module['name']
        if not target.exists():
            print(name + ' installing ...')
            os.makedirs(target)
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
            if proc.returncode == 0:
                print(f'{name} extract success !')
            else:
                print(f'[{cmd!r} exited with {proc.returncode}]')

        with open(os.path.join(target, 'package.json'), 'r') as f:
            package = f.read()
        package = json.loads(package)

        self.task_queue.enqueue([
            AsyncTask(self.script_install, script)
            for script, version in package.get('dependencies', {}).items()
        ])
