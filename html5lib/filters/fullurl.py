import _base
from urlparse import urljoin

attr_val_is_uri = ['href', 'src', 'cite', 'action', 'longdesc',
     'xlink:href', 'xml:base']

class Filter(_base.Filter):
    def __init__(self, source, baseURI):
        _base.Filter.__init__(self, source)
        self.baseURI = baseURI

    def __iter__(self):
        for token in _base.Filter.__iter__(self):
            if token.has_key("data"):
                for i, pair in enumerate(token["data"]):
                    if pair[0] in attr_val_is_uri:
                        token["data"][i] = (pair[0], urljoin(self.baseURI, pair[1]))
            yield token
