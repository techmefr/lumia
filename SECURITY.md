# Security policy

## Supported versions

Lumia has no tagged release yet. Security fixes land on `main` and ship in the `edge` images
(`ghcr.io/techmefr/lumia-backend:edge`, `ghcr.io/techmefr/lumia-web:edge`). Run the latest `main`
to get them; older commits are not patched.

## Reporting a vulnerability

Please do not open a public issue, discussion or pull request for a vulnerability.

Report it privately through GitHub instead:
[**Report a vulnerability**](https://github.com/techmefr/lumia/security/advisories/new). Include what
you can of:

- the affected component (API, worker, web app, extension, mobile app, compose setup) and commit;
- the steps to reproduce it, or a proof of concept;
- what an attacker gains, and under which configuration.

You will get an answer within seven days. Once the issue is confirmed, a fix is prepared in a
private fork, a GitHub security advisory is published with the fix, and you are credited unless you
ask not to be.

## Scope

In scope: the code in this repository and the default `docker-compose.yml` setup, for example
authentication and sessions, access between accounts, server-side request forgery through feed,
page or webhook URLs, injection, and secrets exposed by the API.

Out of scope: vulnerabilities in Miniflux, PostgreSQL, Redis or other upstream projects (report them
upstream), instances exposed without HTTPS or with the API published on purpose
(`LUMIA_API_BIND=0.0.0.0`), and attacks that need control of the host or of the `.env` file.
