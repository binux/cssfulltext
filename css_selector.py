#!/url/bin/python
#-- coding: utf-8 --
'''
make minidom selected by css selector

Create on 2011.2.6

@author: binux
'''

import re
import string

from xml.dom import Node
def fixMiniDom():
    def getElementById(self, id):
        if id in self._id_cache:
             return self._id_cache[id]
        # cache id
        if not self._id_cache:
            for element in self.getElementsByTagName('*'):
                if element.getAttribute("id"):
                    self._id_cache[element.getAttribute("id")] = element
            if id in self._id_cache:
                return self._id_cache[id]

    def getElementsBySelector(self, all_selectors):
        selected = []

        # remove blanks in the right of >
        all_selectors = re.sub('>\s+', '>', all_selectors)

        # Grab all of the tagName elements within current context
        def getElements(context,tag):
            if not tag: tag = '*'

            # Get elements matching tag, filter them for class selector
            found = []
            for con in context:
                eles = con.getElementsByTagName(tag)
                found.extend(eles)

            return found

        context = [self, ]
        inheriters = string.split(all_selectors, " ")

        for element in inheriters:
            # take all
            m = re.match(r'^(>)?(\w+)?(#[a-zA-z0-9\-_]+)?(\.[a-zA-z0-9\-_]+)?(#[a-zA-z0-9\-_]+)?(\[(\w+)([=~!\|\^\$\*]?)=?[\'"]?([^\]\'"]*)[\'"]?\])?$', element)
            if (m):
                _sub = m.group(1)
                _tag = m.group(2)
                _id = m.group(3) or m.group(5)
                _class = m.group(4)
                _css3 = m.group(6)
                _attr = m.group(7)
                _operator = m.group(8)
                _value = m.group(9)
            else:
                continue

            # fix id and class
            if _id: _id = _id[1:]
            if _class: _class = _class[1:]

            found = []
            if _sub:
                for con in context:
                    for each in con.childNodes:
                        if each.nodeType == Node.ELEMENT_NODE:
                            found.append(each)
            elif _id:
                ele = self.getElementById(_id)
                if ele:
                    found = [ele, ]
            else:
                found = getElements(context,_tag)
            
            # tag
            if _tag and _id: # as _id is not exist we get element by tag, so isn't neccessary to test this
                tmp = []
                for fnd in found:
                    if(fnd.tagName == _tag):
                        tmp.append(fnd)
                found = tmp

            # id
            if _id: 
                tmp = []
                for fnd in found:
                    if(fnd.getAttribute("id") and (_id == fnd.getAttribute("id"))): 
                        tmp.append(fnd)
                found = tmp

            # class
            if _class: 
                tmp = []
                for fnd in found:
                    if(fnd.getAttribute("class") and (_class in fnd.getAttribute("class").split())): 
                        tmp.append(fnd)
                found = tmp

            # css3
            if _css3:
                tmp = []
                for fnd in found:
                    if(_operator=='=' and fnd.getAttribute(_attr) != _value): continue
                    if(_operator=='~' and not(re.search(r'(^|\\s)'+_value+'(\\s|$)',  fnd.getAttribute(_attr)))): continue
                    if(_operator=='!' and re.search(r'(^|\\s)'+_value+'(\\s|$)',  fnd.getAttribute(_attr))): continue
                    if(_operator=='|' and not(re.search(r'^'+_value+'-?', fnd.getAttribute(_attr)))): continue
                    if(_operator=='^' and string.find(fnd.getAttribute(_attr), _value)!=0): continue
                    if(_operator=='$' and string.rfind(fnd.getAttribute(_attr), _value) != (fnd.getAttribute(_attr).length-_value.length)): continue
                    if(_operator=='*' and not(string.find(fnd.getAttribute(_attr), _value)+1)): continue

                    elif(not fnd.getAttribute(_attr)): continue
                    tmp.append(fnd)
                found = tmp

            context = found

        selected.extend(context)
        return selected

    from xml.dom import minidom
    setattr(minidom.Element, '_id_cache', {})
    setattr(minidom.Element, 'getElementById', getElementById)
    setattr(minidom.Element, 'getElementsBySelector', getElementsBySelector)
    setattr(minidom.Document, '_id_cache', {})
    setattr(minidom.Document, 'getElementById', getElementById)
    setattr(minidom.Document, 'getElementsBySelector', getElementsBySelector)

fixMiniDom()
