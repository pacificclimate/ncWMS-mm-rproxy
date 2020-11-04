# ncWMS-mm-proxy

A reverse proxy (request forwarder) for ncWMS that translates dataset id's from
static dataset (`modelmeta` `unique_id`) form to dynamic dataset (prefix + filepath) form,
using a `modelmeta` database.

## Run dev

```
export FLASK_APP=ncwms_mm_rproxy
export FLASK_ENV=development
flask run
```
