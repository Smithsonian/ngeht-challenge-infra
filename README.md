# ngEHT Challenge Website Infrastructure

This repo contains infrastructure for the ngEHT Challenge website, namely:

- an nginx configuration file, which mostly serves up static content pages
- a small webserver based on `aiohttp` to handle uploads
- some code to post information about uploads to a Slack channel

The webserver code has support for asynchronously running cpu-intensive tasks (`run_burner()`)
and command line programs (`run_external_exec()`). The latter is currently used to test
the integrity of uploaded zip archives. The webserver also has a route `/upload-test`
intended to be used for uptime monitoring.

The webpages for upload success or failure are templated with Jinja2.

