#!/url/bin/python
#-- coding: utf-8 --
'''
Create on 2011.2.4

@author: binux
'''

def test_parser(filename):
    import feedparser
    import feedformatter

    fp = open(filename, 'r')
    content = fp.read()
    rss = feedparser.parse(content)
    feedparser.PprintSerializer(rss).write()

def test_parser_serilaz(filename):
    import feedparser
    import feedformatter

    fp = open(filename, 'r')
    content = fp.read()
    rss = feedparser.parse(content)
    #feedparser.PprintSerializer(rss).write()

    feed = feedformatter.Feed(rss.feed, rss.entries)
    print feed.format_rss2_string(pretty=True)

def test_insertErrorItem(filename):
    import feedparser
    import feedformatter
    from cron import insertErrorItem

    fp = open(filename, 'r')
    content = fp.read()
    rss = feedparser.parse(content)
    #feedparser.PprintSerializer(rss).write()

    feed = feedformatter.Feed(rss.feed, rss.entries)
    feed_string = feed.format_rss2_string(pretty=True)

    print insertErrorItem(feed_string)

def test_css_selector(filename, selector):
    import html5lib
    import css_selector
    
    fp = open(filename , 'r')
    content = fp.read()
    doc_dom = html5lib.parse(content, 'dom')
    print doc_dom.getElementsBySelector(selector)

def main():
    test_parser('./doc/feed')
    #test_parser_serilaz('./doc/feed')
    #test_insertErrorItem('cnbate.rss')
    #test_css_selector('/home/binux/downloads/google-appengine-docs-20110105/appengine/docs/python/taskqueue/tasks.html', 'div.g-unit#gc-toc')
    pass


if __name__ == '__main__':
    main()
