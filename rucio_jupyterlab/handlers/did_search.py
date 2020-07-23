import json
import tornado
from rucio_jupyterlab.db import get_db
from rucio_jupyterlab.rucio.authenticators import RucioAuthenticationException
import rucio_jupyterlab.utils as utils
from .base import RucioAPIHandler

class WildcardDisallowedException(BaseException):
    pass

class DIDSearchHandlerImpl:
    def __init__(self, namespace, rucio):
        self.namespace = namespace
        self.rucio = rucio
        self.db = get_db()  # pylint: disable=invalid-name

    def search_did(self, scope, name, search_type):
        wildcard_enabled = self.rucio.instance_config.get('wildcard_enabled', False)

        if ('*' in name or '%' in name) and not wildcard_enabled:
            raise WildcardDisallowedException()

        dids = self.rucio.search_did(scope, name, search_type)

        def mapper(entry, _):
            return {
                'did': entry.get('scope') + ':' + entry.get('name'),
                'size': entry.get('bytes'),
                'type': entry.get('did_type').lower()
            }

        result = utils.map(dids, mapper)
        return result


class DIDSearchHandler(RucioAPIHandler):
    @tornado.web.authenticated
    def get(self):
        namespace = self.get_query_argument('namespace')
        search_type = self.get_query_argument('type', 'collection')
        did = self.get_query_argument('did')
        rucio = self.rucio.for_instance(namespace)

        (scope, name) = did.split(':')
        handler = DIDSearchHandlerImpl(namespace, rucio)

        try:
            dids = handler.search_did(scope, name, search_type)
            self.finish(json.dumps(dids))
        except RucioAuthenticationException:
            self.set_status(401)
            self.finish(json.dumps({'error': 'authentication_error'}))
        except WildcardDisallowedException:
            self.set_status(400)
            self.finish(json.dumps({'error': 'wildcard_disabled'}))
