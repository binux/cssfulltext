#!/url/bin/python
#-- coding: utf-8 --
'''
Create on 2011.2.3

@author: binux
'''

import hashlib
import datetime
import feedparser
import feedformatter
import fetcher

from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import search

RETRY_TIMES_60 = 3
RETRY_TIMES_PROJECT = 20
RETRY_TIMES_1DAYS = 120
RETRY_INTERVAL  = datetime.timedelta(0, 60)

class Project(search.SearchableModel):
    name = db.StringProperty(required=True)
    link = db.LinkProperty(required=True)
    description = db.StringProperty(multiline=True)
    user = db.UserProperty(required=True)
    contentSelector = db.StringProperty(multiline=True)
    filterSelector = db.StringProperty(multiline=True)
    encoding = db.StringProperty(default=None)

    contentHash = db.StringProperty()
    resultCache = db.TextProperty()

    createdDate = db.DateTimeProperty(required=True, auto_now_add=True)
    lastModifiedDate = db.DateTimeProperty(required=True, auto_now_add=True)
    lastUpdateDate = db.DateTimeProperty(required=True, auto_now=True)
    nextUpdateDate = db.DateTimeProperty(required=True, auto_now_add=True)

    subscriptCount = db.IntegerProperty()
    updateFrequent = db.IntegerProperty()
    retryCount = db.IntegerProperty(default=0)
    comments = db.StringProperty()
    inValid = db.BooleanProperty(required=True,default=False)

    @classmethod
    def SearchableProperties(cls):
        return [['name','link', 'description']]

def insertErrorItem(rss_string):
    from os import environ
    rss_dict = feedparser.parse(rss_string)
    ErrorMessageItem= {}
    ErrorMessageItem["title"] = "your feed is invalid"
    ErrorMessageItem["link"] = "http://%s.appspot.com" % environ['APPLICATION_ID']
    ErrorMessageItem["description"] = "Your feed made by is no more valid."
    ErrorMessageItem["guid"] = "Feed Invalid at "+datetime.datetime.now()
    rss_dict.entries.insert(0, ErrorMessageItem)
    feed = feedformatter.Feed(rss_dict.feed, rss_dict.entries)
    return feed.format_rss2_string(validate=False, pretty=True)

def updateProject(project):
    if datetime.datetime.now() - project.lastUpdateDate < datetime.timedelta(minutes=1): 
        return 
    elif project.inValid: 
        project.nextUpdateDate = datetime.datetime.max
        return
    else:
        forceUpdateProject(project)

def forceUpdateProject(project):
    # step 1: fetch rss
    def tempFail():
        project.retryCount += 1
        if project.retryCount < RETRY_TIMES_60:
            project.nextUpdateDate += RETRY_INTERVAL
        elif project.retryCount < RETRY_TIMES_PROJECT:
            project.nextUpdateDate += datetime.timedelta(seconds=project.updateFrequent)
        elif project.retryCount < RETRY_TIMES_1DAYS:
            project.nextUpdateDate += datetime.timedelta(days=1)
        else:
            project.nextUpdateDate = datetime.datetime.max
            project.resultCache = insertErrorItem(project.resultCache)
            project.inValid = True

    try:
        response = urlfetch.fetch(project.link)
    except urlfetch.InvalidURLError, e:
        project.inValid = True
        project.put()
        return
    except (urlfetch.DownloadError, urlfetch.ResponseTooLargeError), e:
        tempFail()
        project.put()
        return

    if response.status_code != 200:
        tempFail()
        project.put()
        return
    elif hashlib.md5(response.content).hexdigest() == project.contentHash:
        # step 1.5(1): nothing change
        project.retryCount = 0
        project.nextUpdateDate += datetime.timedelta(seconds=project.updateFrequent)
        project.put()
        return
    else:
        # step 1.5(2): set project status
        project.contentHash = hashlib.md5(response.content).hexdigest()
        project.retryCount = 0
        project.nextUpdateDate += datetime.timedelta(seconds=project.updateFrequent)

    # step 2: parse rss
    rss_dict = feedparser.parse(response.content, response_headers=response.headers)
    
    # step 3: get each descriptions
    for entry in rss_dict.entries:
        if not entry.has_key('link'):
            continue

        new_description = fetcher.fetch_description(entry.link, project)
        if new_description:
            entry['summary'] = new_description

    # step 4: save result to database
    feed = feedformatter.Feed(rss_dict.feed, rss_dict.entries)
    feed_content = feed.format_rss2_string(validate=False, pretty=True)
    # add project dtd
    project.resultCache = '<?xml version="1.0" encoding="utf-8"?>' + feed_content

    project.put()
