#!/url/bin/python
#-- coding: utf-8 --
'''
Create on 2011.2.1

@author: binux
'''

import logging
import hashlib
import html5lib
import css_selector

from html5lib.filters import fullurl

from google.appengine.ext import db
from google.appengine.api import urlfetch

_parse = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("dom")).parse
_walker = html5lib.treewalkers.getTreeWalker("dom")
_serialize = html5lib.serializer.htmlserializer.HTMLSerializer(
        omit_optional_tags=False, 
        quote_attr_values=True).serialize

class DescriptionCache(db.Model):
    link = db.StringProperty(required=True)
    project_id = db.IntegerProperty(required=True)
    description = db.TextProperty()

    retryCount = db.IntegerProperty(required=True, default=3)
    createdDate = db.DateTimeProperty(required=True, auto_now_add=True)
    lastVisitedDate = db.DateTimeProperty(required=True, auto_now=True)

def fetch_description(url, project):
    des_cache = DescriptionCache.get_by_key_name(hashlib.md5(str(project.key().id())+url).hexdigest())
    if des_cache is None:
        description = real_fetch_description(url, project.contentSelector, project.filterSelector, project.encoding)
        if description:
            des_cache = DescriptionCache.get_or_insert(hashlib.md5(str(project.key().id())+url).hexdigest(), 
                    link=url, project_id = project.key().id(), description=db.Text(description))
            des_cache.put()
    else:
        description = des_cache.description
        des_cache.put()

    return description

def real_fetch_description(url, content_selector, filter_selector, encoding=None):
    try:
        response = urlfetch.fetch(url)
    except urlfetch.InvalidURLError, e:
        return u''
    if response.status_code != 200:
        raise Exception, "status code: response.status_code"

    doc_dom = _parse(response.content, encoding=encoding)
    content_dom = []
    for each in [x for x in content_selector.split('\n') if x]:
        dom = doc_dom.getElementsBySelector(each)
        content_dom.extend(dom)
    content_dom = set(content_dom)

    filter_dom = []
    for each_content in content_dom:
        for each_selector in [x for x in filter_selector.split('\n') if x]:
            dom = each_content.getElementsBySelector(each_selector)
            filter_dom.extend(dom)
    filter_dom = set(filter_dom)
    for each_dom in filter_dom:
        if each_dom.parentNode:
            each_dom.parentNode.removeChild(each_dom)

    contents = []
    for dom in content_dom:
        w = _walker(dom)
        w = fullurl.Filter(w, url)
        for item in _serialize(w):
            contents.append(item)
    return u''.join(contents)
