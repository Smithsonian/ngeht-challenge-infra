import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
import functools
import time
import logging
import json
import re
import random

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape

from slack_sdk.webhook.async_client import AsyncWebhookClient


mp_thread_count = 1

template_stuff = {
    'title': 'ngEHT Analysis Challenge',
    'baseurl': '//challenge.bx9.net/',
}

outputdir = '/home/astrogreg/github/ngeht-analysis-content/uploads'


LOGGER = logging.getLogger(__name__)
mp_executor = ProcessPoolExecutor(mp_thread_count)


async def run_burner(wrap):
    '''Helper function to asynchronously run a blocking cpu-intensive task on another core

    wrap = functools.partial(func, args...)
    '''
    return await asyncio.ensure_future(asyncio.get_event_loop().run_in_executor(mp_executor, wrap))


async def run_external(cmd):
    '''Helper function to run a non-blocking external command. cmd is a list.'''
    proc = await asyncio.create_subprocess_shell(cmd,
                                                 stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


def example_burn(arg):
    t0 = time.time()
    while time.time() - t0 < float(arg):
        pass
    return str(arg)


async def app_factory():
    # asyncio is started at this point
    return app


def get_slack_webhook():
    env = os.getenv('SERVER_SLACK_WEBHOOK')
    if env is not None:
        return env

    slack_secrets_file = '~/.slack_secrets'
    try:
        with open(os.path.expanduser(slack_secrets_file), 'r') as fp:
            secrets = json.load(fp)
    except Exception:
        LOGGER.exception('slack secret json load from ~/.slack_secrets failed')
        return
    try:
        url = secrets['webhooks']['Event Horizon Telescope']['ngeht-challenge-bots']
    except Exception:
        LOGGER.exception('slack secret json key not found in ~/.slack_secrets')
        return

    return AsyncWebhookClient(url)


async def slack_message(text, webhook):
    if webhook is None:
        LOGGER.warning('not sending slack message because webhook is not configured: '+text)
        return

    #response = await webhook.send(text=text)

    print('would have sent to slack:')
    print(text)
    return

    if response.status_code != 200:
        LOGGER.warning('abnormal response status from slack webhook: {}'.format(response.status_code))
    elif response.body != 'ok':
        LOGGER.warning('abnormal response body from slack webhook: '+response.body)


def upload_get_challenge(fields, problems):
    challenge = None
    if 'challenge' not in fields:
        challenge = 'unknown'  # we will rename later
    else:
        challenge = fields['challenge']
        if not re.fullmatch(r'challenge\d', challenge):
            # this also checks that the challenge field is sane enough to be used in a file path
            problems.append('challenge must be challenge followed by a single digit')
            LOGGER.warn('challenge of {} does not follow pattern challengeN'.format(challenge))
    return challenge


def upload_rename_upload(outfile, fields, problems):
    if not outfile:
        return
    if '/unknown/' in outfile:
        if 'challenge' not in fields:
            problems.append('challenge field not present in form')
            return
        challenge = upload_get_challenge(fields, problems)
        new_outfile = upload_get_outfile(outputdir, challenge, problems)
        # both directories exist, so rename the file
        try:
            os.rename(outfile, new_outfile)
        except Exception as e:
            problems.append('{} exception renaming upload file to final name'.format(str(e)))
            LOGGER.exception('{} exception renaming upload file to final name'.format(str(e)))
        # attempt to get rid of the /unknown/ directory, which ought to be empty
        try:
            os.unlink(os.path.dirname(outfile))
        except Exception as e:
            LOGGER.exception('{} exception removing temporary upload directory'.format(str(e)))
    return new_outfile


def upload_get_outfile(outputdir, challenge, problems):
    outfile = None
    if not problems:
        challenge_outputdir = outputdir + '/' + challenge + '/'
        if not os.path.isdir(challenge_outputdir):
            problems.append(challenge + ' output dir {} does not exist'.format(challenge_outputdir))
            return

        while True:
            r = str(random.randint(100, 999))
            full_outputdir = challenge_outputdir + r
            if os.path.isdir(full_outputdir):
                continue
            os.makedirs(full_outputdir, exist_ok=True)
            outfile = full_outputdir + '/{}.zip'.format(r)
            break
    print('outfile is', outfile)
    return outfile


async def upload_file(zipfilereader, outfile, fields, problems):
    if not zipfilereader:
        # someone else appended a problem
        return
    if zipfilereader and problems:
        problems.append('did not upload or check .zip file due to previous problems')
        return

    length = 0
    try:
        with open(outfile, 'wb') as fd:
            while True:
                # nginx is enforcing a max size, so we don't have to worry
                chunk = await zipfilereader.read_chunk()
                if not chunk:
                    break
                fd.write(chunk)
                length += len(chunk)
    except Exception as e:
        problems.append('{} exception seen processing file upload'.format(str(e)))
        LOGGER.exception('Exception seen during file upload')
        length = None
    fields['zipsize'] = length


async def upload_parse_form(reader, problems):
    fields = {}
    zipfilereader = None
    outfile = None
    while True:
        field = await reader.next()
        if not field:
            break
        if field.name != 'zip':
            fields[field.name] = await field.text()
            print('field', field.name, '=', repr(fields[field.name]))
            continue

        print('field zip')
        zipfilereader = field
        filename = zipfilereader.filename
        fields['filename'] = filename
        if not filename.lower().endswith('.zip'):
            problems.append('filename did not end with .zip')
            continue
        # we have to read the file right away... and the form "challenge" field might be later
        challenge = upload_get_challenge(fields, problems)
        outfile = upload_get_outfile(outputdir, challenge, problems)
        await upload_file(zipfilereader, outfile, fields, problems)

    if not zipfilereader:
        problems.append('no zip file specified in form')

    return fields, outfile


def upload_check_one_of(fields, problems):
    one_of = ('name', 'email', 'team')
    if not any([fields[x] for x in one_of]):
        problems.append('must specify at least one of email, name, or team name')


async def upload_test(outfile, fields, problems):
    '''
zip -Tv foo.zip 
Archive:  foo.zip
    testing: requirements.txt         OK
No errors detected in compressed data of foo.zip.
test of foo.zip OK
'''
    if not outfile:
        return
    cmd = 'zip -Tv ' + outfile
    print(cmd)
    returncode, stdout, stderr = await run_external(cmd)

    if returncode != 0:
        problems.append('zip file arrived corrupted (return code {})'.format(returncode))
        return

    filelist = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith('testing: ') and line.endswith(' OK'):
            filelist.append(line[9:-3].strip())

    print('{} is good and the files in it are:')
    print(' ', '\n  '.join(filelist))

    # TODO: check filenames?


def upload_log(fail, fields, problems):
    s = 'failure' if fail else 'success'
    LOGGER.info('Upload '+s)
    for k, v in fields.items():
        LOGGER.info(k + ': ' + v)
    for p in problems:
        LOGGER.info('problem: ' + p)


async def upload_slack_response(fail, fields, problems, webhook):
    t = 'upload failure!' if fail else 'upload success!'
    t += ' ' + ' / '.join(fields.values())
    if problems:
        t += '\n' + ' / '.join(problems)
    await slack_message(t, webhook)


def upload_response(fail, fields, problems):
    t = 'upload_failure.html' if fail else 'upload_success.html'
    template = env.get_template(t)
    html = template.render(stuff=template_stuff, fields=fields, problems=problems)
    return web.Response(text=html, content_type='text/html')


async def upload_log_and_respond(fields, problems, slack_webhook):
    # flesh out fields to include all fields for templating
    for f in ('name', 'email', 'team', 'filename', 'zipsize'):
        if f not in fields or fields[f] is None:
            fields[f] = 'None'
    if 'zipsize' in fields:
        fields['zipsize'] = str(fields['zipsize']) + ' bytes'

    if problems:
        fail = True
    else:
        fail = False

    await upload_slack_response(fail, fields, problems, slack_webhook)  # TODO: get local name into slack message NNN.zip
    upload_log(fail, fields, problems)  # TODO: create a file with this info, not just slack.
    return upload_response(fail, fields, problems)


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

    problems = []
    fields, outfile = await upload_parse_form(reader, problems)
    outfile = upload_rename_upload(outfile, fields, problems)

    upload_check_one_of(fields, problems)
    await upload_test(outfile, fields, problems)

    return await upload_log_and_respond(fields, problems, slack_webhook)

# TODO: compute metrics?
# TODO: figure out how to do processing after the return (asyncio background task)


app = web.Application()
app.add_routes(routes)

env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape(['html'])
)

loglevel = os.getenv('SERVER_LOGLEVEL')  # DEBUG, etc
logging.basicConfig(level=loglevel)

slack_webhook = get_slack_webhook()

port = int(os.getenv('PORT', '8001'))
web.run_app(app_factory(), host='localhost', port=port, reuse_port=True)
