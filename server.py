import asyncio
import os
import sys
from concurrent.futures import ProcessPoolExecutor
import functools
import time
import logging

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape

mp_thread_count = 1

template_stuff = {
    'title': 'ngEHT Analysis Challenge',
    'baseurl': '//challenge.bx9.net/',
}

outputdir = ''


LOGGER = logging.getLogger(__name__)
executor = ProcessPoolExecutor(mp_thread_count)


async def run_burner(wrap):
    '''Helper function to run a cpu-intensive non-blocking task.

    wrap = functools.partial(func, args...)
    '''
    return await asyncio.ensure_future(asyncio.get_event_loop().run_in_executor(executor, wrap))


async def run_external(cmd):
    '''Helper function to run a non-blocking external command. cmd is a list.'''
    proc = await asyncio.create_subprocess_shell(cmd,
                                                 stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout, stderr


def example_burn(arg):
    t0 = time.time()
    while time.time() - t0 < float(arg):
        pass
    return str(arg)


async def app_factory():
    # asyncio is started at this point
    return app


def upload_response(fail, fields, problems):
    t = 'upload_failure.html' if fail else 'upload_success.html'
    template = env.get_template(t)
    html = template.render(stuff=template_stuff, fields=fields, problems=problems)
    return web.Response(text=html, content_type='text/html')


def upload_log(fail, fields, problems):
    s = 'failure' if fail else 'success'
    LOGGER.info('Upload '+s)
    for k, v in fields.items():
        LOGGER.info(k + ': ' + v)
    for p in problems:
        LOGGER.info('problem: ' + p)


routes = web.RouteTableDef()


@routes.get('/testing/fork/sleep_10')
async def do_fork_sleep_10(request):
    await run_external('sleep 10')
    return web.Response(status=200, text='sleep 10', content_type='text/plain')


@routes.get('/testing/fork/burn_10')
async def do_fork_burn_10(request):
    wrap = functools.partial(example_burn, 10.0)
    ret = await run_burner(wrap)
    return web.Response(status=200, text=ret, content_type='text/plain')


@routes.post('/upload')
async def upload_wrapper(request):
    LOGGER.info('start of upload')
    try:
        ret = await upload(request)
    except web.HTTPException:
        LOGGER.exception('raising HTTPException in upload try/except')
        raise
    except Exception as e:
        LOGGER.exception('Exception in the webserver upload code')
        ret = 'Greg''s upload code just crashed with exception '+str(e)
        return web.Response(status=500, text=ret, content_type='text/plain')
    return ret


async def upload(request):
    reader = await request.multipart()  # this is a MultipartReader
    fields = {}
    problems = []
    while True:
        field = await reader.next()
        if not field:
            break
        if field.name != 'zip':
            fields[field.name] = await field.text()
            continue

        # select output filename
        filename = field.filename
        fields['filename'] = filename
        if not filename.lower().endswith('.zip'):
            problems.append('filename did not end with .zip')
            fields['zipsize'] = 'None'  # avoid printing 2 problems
            break

        length = 0
        while True:
            # nginx is enforcing a max size, so we don't have to worry
            chunk = await field.read_chunk()
            if not chunk:
                break
            length += len(chunk)
        fields['zipsize'] = length

    # validate
    if 'zipsize' not in fields:
        problems.append('no zip file specified')

    one_of = ('name', 'email', 'team')
    if not any([x in fields for x in one_of]):
        problems.append('must specify at least one of email, name, or team name')

    # TODO: validate filenames from "zip -t" -- inexpensive, just reads the end of the file
    # TODO: send slack to datacrew that we have a new upload

    # flesh out fields to include all fields for templating
    all_fields = [*one_of, 'filename', 'zipsize']
    for f in all_fields:
        if f not in fields:
            fields[f] = 'None'

    if problems:
        fail = True
    else:
        fail = False

    # TODO: slack notification

    upload_log(fail, fields, problems)
    return upload_response(fail, fields, problems)

    # TODO: figure out how to do processing after the return (asyncio background task)
    # TODO: compute metrics?


app = web.Application()
app.add_routes(routes)

env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape(['html'])
)

loglevel = os.getenv('SERVER_LOGLEVEL')  # DEBUG, etc
logging.basicConfig(level=loglevel)

port = int(os.getenv('PORT', '8001'))
web.run_app(app_factory(), host='localhost', port=port, reuse_port=True)
