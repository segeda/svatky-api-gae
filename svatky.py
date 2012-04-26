# coding: utf-8
#
# Copyright (c) 2011, Petr Severa
# For the full copyright and license information, please view the file LICENSE.txt that was distributed with this source code.

"""Svátky API"""


import os
from datetime import datetime
from datetime import timedelta

from google.appengine.dist import use_library
use_library('django', '1.2')

from django.utils import simplejson

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


def get_svatky(self_request, format):
	svatky = []
	lang = 'cs'
	name = self_request.get('name')
	date = self_request.get('date')
	
	if self_request.get('lang') == 'sk':
		import sk as slovnik
		lang = 'sk'
	else:
		import cs as slovnik
	
	if not name and not date:
		date = datetime.now().strftime('%d%m')
	
	if name:
		response = memcache.get(format + name + lang)
		if response:
			return response
		else:
			if name in slovnik.jmeno:
				for datum in slovnik.jmeno[name]:
					svatek = datum, name
					svatky.append(svatek)
			response = get_format(set(svatky), format)
			memcache.add(format + name + lang, response, 86400)
			return response
	
	if date:
		response = memcache.get(format + date + lang)
		if response:
			return response
		else:
			if date in slovnik.datum:
				for jmeno in slovnik.datum[date]:
					svatek = date, jmeno
					svatky.append(svatek)
			response = get_format(set(svatky), format)
			memcache.add(format + date + lang, response, 86400)
			return response
	

def get_format(set_svatky, format):
	if format == 'txt':
		return get_txt(set_svatky)
	
	if format == 'xml':
		return get_xml(set_svatky)
	
	if format == 'json':
		return get_json(set_svatky)


def get_txt(set_svatky):
	txt = ''
	for svatek in set_svatky:
		txt += '%s;%s\n' % svatek
	return txt


def get_xml(set_svatky):
	xml = '<?xml version="1.0" encoding="UTF-8"?>'
	xml += '<svatky>'
	for svatek in set_svatky:
		xml += '<svatek><date>%s</date><name>%s</name></svatek>' % svatek
	xml += '</svatky>'
	return xml


def get_json(set_svatky):
	jsonData = []
	for svatek in set_svatky:
		jsonData.append({'date':svatek[0], 'name':svatek[1]})
	return simplejson.dumps(jsonData)


def set_headers(request_handler):
	time_format = '%a, %d %b %Y %H:%M:%S GMT'
	last_modified = datetime.strptime(datetime.now().strftime('%a, %d %b %Y 00:00:00 GMT'), time_format)
	expires = last_modified + timedelta(days=1)
	
	if 'If-Modified-Since' in request_handler.request.headers:
		modified_since = datetime.strptime(request_handler.request.headers.get('If-Modified-Since'), time_format)
		if modified_since >= last_modified:
			request_handler.error(304)
			return
	
	request_handler.response.headers['Access-Control-Allow-Origin'] = '*'
	request_handler.response.headers['Cache-Control'] = 'max-age=600'
	request_handler.response.headers['Last-Modified'] = last_modified.strftime(time_format)
	request_handler.response.headers['Expires'] = expires.strftime(time_format)


class Index(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
		self.response.out.write(template.render(path, {}))


class Txt(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain; charset=UTF-8'
		set_headers(self)
		self.response.out.write(get_svatky(self.request, 'txt'))


class Xml(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/xml; charset=UTF-8'
		set_headers(self)
		self.response.out.write(get_svatky(self.request, 'xml'))


class Json(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		set_headers(self)
		self.response.out.write(get_svatky(self.request, 'json'))


application = webapp.WSGIApplication(
	[('/', Index),
	('/txt', Txt),
	('/xml', Xml),
	('/json', Json)],
	debug=True)


def main():
	run_wsgi_app(application)


if __name__ == "__main__":
	main()
