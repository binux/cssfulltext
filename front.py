#!/url/bin/python
#-- coding: utf-8 --
'''
Create on 2011.2.5

@author: binux
'''

import re
import random
import logging
import datetime
import fix_path
import feedparser
import feedformatter

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import search
from google.appengine.api import urlfetch
from google.appengine.runtime import DeadlineExceededError
from project import Project
from fetcher import DescriptionCache, real_fetch_description, fetch_description
from hashlib import md5

class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        template_values = {
                'user'     : user,
                'login'    : users.create_login_url(self.request.uri),
                'logout'   : users.create_logout_url(self.request.uri),
                }
        self.response.out.write(template.render('template/index.html', template_values))

class SearchPage(webapp.RequestHandler):
    def get(self, query_type):
        user = users.get_current_user()
        query = self.request.get('q')
        if query_type == 'user':
            query = users.User(query)
            projects = list(db.GqlQuery("SELECT * FROM Project WHERE %s = :1" % query_type, query))
        else:
            projects = Project.all().search(query, properties=['name', 'link', 'description']).fetch(20)
        template_values = {
                'user'     : user,
                'login'    : users.create_login_url(self.request.uri),
                'logout'   : users.create_logout_url(self.request.uri),
                'projects' : projects,
                }
        if query_type == 'all':
            try:
                template_values['link'] = db.Link(query)
            except Exception:
                pass
        self.response.out.write(template.render('template/search.html', template_values))

class EditorPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()

        _id   = self.request.get_range('id')
        _link = self.request.get('link')
        _saved = self.request.get('saved')

        if _id == 0:
            project = {
                    'key'     : {'id' : 0},
                    'name'    : '',
                    'link'    : _link,
                    'description'   : '',
                    'user'    : {'email' : user and user.email() or 'You'},
                    'contentSelector'   : '',
                    'filterSelector'    : '',
                    }
            is_valid = bool(user)
        else:
            project = Project.get_by_id(_id)
            if not project:
                # TODO:使用统一的Error报告页
                self.response.set_status(400)
                self.response.out.write("project 未找到")
                return
            is_valid = bool(project.user == user or users.is_current_user_admin())
        template_values = {
                'user'     : user,
                'login'    : users.create_login_url(self.request.uri),
                'logout'   : users.create_logout_url(self.request.uri),
                'project'  : project,
                'is_valid' : is_valid,
                'saved'   : _saved,
                }
        self.response.out.write(template.render('template/editor.html', template_values))

    def post(self):
        user = users.get_current_user()
        if not user:
            self.response.set_status(403)
            self.response.out.write('这个操作需要登录')
            return
            
        _id   = self.request.get_range('id')
        _link = db.Link(self.request.get('link'))
        _name = self.request.get('name')
        _description = self.request.get('description')
        _content = self.request.get('content')
        _filter = self.request.get('filter')
        _delete = self.request.get('delete')
        _encoding = None
        m = re.search(r"^#.*?encoding.*?([a-zA-z0-9\-_]+)", _description, re.M)
        if m:
            _encoding = m.group(1)

        if not _delete and _id == 0: 
            project = Project(link=_link, name=_name, description=_description, user=user, contentSelector=_content, filterSelector=_filter, encoding=_encoding)
            project.save()
            self.redirect('/e/?id='+str(project.key().id())+'&saved=1')
        elif _id != 0:
            project = Project.get_by_id(_id)
            if project and project.link == _link and (project.user == user or users.is_current_user_admin()):
                should_remove_cache = False
                if _delete or project.contentSelector != _content or project.filterSelector != _filter or project.encoding == _encoding:
                    should_remove_cache = True

                if _delete:
                    project.delete()
                    self.redirect('/s/user/?q='+user.email())
                else:
                    project.name = _name
                    project.description = _description
                    project.contentSelector = _content
                    project.filterSelector = _filter
                    project.encoding = _encoding
                    project.lastModifiedDate = datetime.datetime.now()
                    project.save()
                    self.redirect('/e/?id='+str(project.key().id())+'&saved=1')
                if should_remove_cache:
                    q = db.GqlQuery("SELECT __key__ FROM DescriptionCache WHERE project_id = :1", project.key().id())
                    r = q.fetch(q.count())
                    db.delete(r)
            else:
                self.response.set_status(400)
                self.response.out.write("无法找到porject。或您没有修改权限")
        else:
            self.response.set_status(400)
            self.response.out.write("无法找到porject。")

class TestPage(webapp.RequestHandler):
    def get(self):
        import feedparser

        #_id   = self.request.get_range('id')
        _link = db.Link(self.request.get('link'))
        #_name = self.request.get('name')
        _description = self.request.get('description')
        _content = self.request.get('content')
        _filter = self.request.get('filter')
        _encoding = None
        m = re.match(r"^#.*?encoding.*?([a-zA-z0-9\-_]+)", _description)
        if m:
            _encoding = m.group(1)

        # get rss
        try:
            response = urlfetch.fetch(_link)
        except Exception, e:
            self.response.out.write(e)
            return
        rss_dict = feedparser.parse(response.content, response_headers=response.headers)
        # get description
        sample = random.choice(rss_dict.entries)
        try:
            fulltext = real_fetch_description(sample.link, _content, _filter, _encoding)
        except Exception, e:
            self.response.out.write(e)
            return

        template_values = {
                'sample'   : sample,
                'fulltext' : fulltext,
                #'_id'      : _id,
                '_link'    : _link,
                #'_name'    : _name,
                #'_description' : _description,
                '_content'     : _content,
                '_filter'      : _filter,
                }
        self.response.out.write(template.render('template/test.html', template_values))

    post = get

class GetFeed(webapp.RequestHandler):
    def get(self, _id):
        _id = int(_id)
        try:
            project = Project.get_by_id(_id)
        except Exception, e:
            self.response.set_status(500)
            self.response.out.write(e)

        # step 1: fetch rss
        if not project:
            self.response.set_status(400)
            self.response.out.write("project 未找到")
            return
        try:
            response = urlfetch.fetch(project.link)
        except urlfetch.InvalidURLError, e:
            self.response.set_status(400)
            self.response.out.write(e)
            return
        except (urlfetch.DownloadError, urlfetch.ResponseTooLargeError), e:
            self.response.set_status(504)
            self.response.out.write(e)
            return
        if response.status_code != 200:
            self.response.set_status(response.status_code)
            self.response.out.write('status code: '+response.status_code)
            return
        # check cache
        if md5(response.content).hexdigest() == project.contentHash:
            logging.debug("using project cache")
            self.response.out.write(project.resultCache)
            return
        # step 2: parse rss
        rss_dict = feedparser.parse(response.content, response_headers=response.headers)
        try:
            # step 3: get each descriptions
            new_entries = []
            for entry in rss_dict.entries:
                if not entry.has_key('link'):
                    continue
                new_description = fetch_description(entry.link, project)
                if new_description:
                    entry['summary'] = new_description
                new_entries.append(entry)
            # step 4: out put feed
            feed = feedformatter.Feed(rss_dict.feed, new_entries)
            feed_content = feed.format_rss2_string(validate=False, pretty=True)
            output = '<?xml version="1.0" encoding="utf-8"?>' + feed_content
            self.response.out.write(output)
            # step 5: save cache
            def update_project(key, contentHash, resultCache):
                project = db.get(key)
                project.contentHash = contentHash
                project.resultCache = resultCache
                project.put()
            db.run_in_transaction(update_project, project.key(), 
                    md5(response.content).hexdigest(), db.Text(output, encoding="utf-8"))
        except DeadlineExceededError:
            feed = feedformatter.Feed(rss_dict.feed, new_entries)
            feed_content = feed.format_rss2_string(validate=False, pretty=True)
            output = '<?xml version="1.0" encoding="utf-8"?>' + feed_content
            self.response.out.write(output)

application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/s/(all|user)/', SearchPage),
    ('/e/', EditorPage),
    ('/p/', TestPage),
    ('/a/(\d+)', GetFeed),
    ])
def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
