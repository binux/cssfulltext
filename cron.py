#!/url/bin/python
#-- coding: utf-8 --
'''
Create on 2011.2.3

@author: binux
'''

import datetime

from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from project import Project, updateProject
from fetcher import DescriptionCache

class updateProjects(webapp.RequestHandler):
    def get(self):
        projects = db.GqlQuery("SELECT __key__ FROM Project WHERE nextUpdateDate < :1", datetime.datetime.now())
        for key in projects:
            task = taskqueue.Task(url='/worker/update_project', params={'key': key.id()})
            task.add('project')

class removeCache(webapp.RequestHandler):
    def get(self):
        task = taskqueue.add(url='/worker/remove_cache')

    def post(self):
        q = db.GqlQuery("SELECT __key__ FROM DescriptionCache WHERE lastVisitedDate < :1", 
                datetime.datetime.now() - datetime.timedelta(days=7))
        r = q.fetch(q.count())
        db.delete(r)

class updateProjectWorker(webapp.RequestHandler):
    def post(self):
        key = self.request.get('key')
        project = Project.get_by_id(key)
        if project:
            updateProject(project)
        else:
            logging.warning("Unknow project key: %s" % key)

def main():
    run_wsgi_app(webapp.WSGIApplication([
            ('/cron/remove_cache', removeCache),
            ('/worker/remove_cache', removeCache),
            ('/cron/update_project', updateProjects),
            ('/worker/update_project', updateProjectWorker),
    ], debug=True))

if __name__ == '__main__':
    main()
