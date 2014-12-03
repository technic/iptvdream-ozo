# -*- coding: utf-8 -*-
#  Dreambox Enigma2 iptv player
#
#  Copyright (c) 2013 Alex Revetchi <revetski@gmail.com>
#  Copyright (c) 2010 Alex Maystrenko <alexeytech@gmail.com>
#  web: http://techhost.dlinkddns.com/
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2, or (at your option) any later
# version.

from abstract_api import MODE_VIDEOS
from ozo_api import OzoAPI
from . import tdSec, secTd, syncTime, Bouquet, Video, unescapeEntities

class e2iptv(OzoAPI):
	
	MODE = MODE_VIDEOS
	iName = "OzoMovies"
	NEXT_API = "OzoTV"
	
	def __init__(self, username, password):
		OzoAPI.__init__(self, username, password)
		
		self.video_genres = []
		self.videos = {}
		self.filmFiles = {}
		self.currentPageIds = []
	
	def getVideos(self, stype='last', page=1, genre=[],  limit=19, query=''):
		self.videos = {}
						
		params = {"limit" : limit,
			"extended": 1,	
			"page" : page }
		if genre and len(genre):
			params['genre'] = "|".join(genre)
		response = self.getJsonData(self.site+"/get_list_movie?", params, "getting video list by type %s" % stype)
		videos_count = int(response['options']['count'])
		
		self.currentPageIds = []
		for v in response['groups']:
			vid = int(v['id'])
			self.currentPageIds += [vid]
			video = Video(v['title'].encode('utf-8'))
			video.name_orig = v['title'].encode('utf-8')
			video.descr = unescapeEntities(v['description']).encode('utf-8')
			video.image = v['pic'].encode('utf-8')
			video.year = v['year'].encode('utf-8')
			video.rate_imdb = 0 #floatConvert(v.findtext('rate_imdb'))
			video.rate_kinopoisk = 0 #floatConvert(v.findtext('rate_kinopoisk'))
			video.rate_mpaa = '' #v.findtext('rate_mpaa')
			video.country = v['country'].encode('utf-8')
			video.genre = v['genre'].encode('utf-8')
			video.length = int(v['time'].encode('utf-8')) / 60
			self.videos[vid] = video				
		return videos_count 
	
	def getVideoInfo(self, vid):
		if not vid in self.videos.keys():
			return False
		video = self.videos[vid] 
		video.director = ''
		video.scenario = ''
		video.actors = ''
		video.studio = ''
		video.awards = ''
		video.budget = ''
		video.files = [vid]
		self.filmFiles[vid] = {'format':'', 'length': video.length, 'name': video.name_orig,'title': video.name_orig, 'traks':['default']}
		self.videos[vid]= video
		return True
	
	def getVideoUrl(self, cid):
		params = {"cid": cid}
		response = self.getJsonData(self.site+"/get_url_movie?", params, "getting video url %s" % cid)
		return response['url'].encode('utf-8')
	
	def getVideoGenres(self):
		response = self.getJsonData(self.site+"/get_gql_movie?", {}, "getting genres list")		
		self.video_genres = [{"id": genre['id'], "name": genre['title'].encode('utf-8')} for genre in response['groups']['genre']]
	
	def getPosterPath(self, vid, local=False):
		if local:
			return self.videos[vid].image.split('/')[-1]
		else:	
			return self.videos[vid].image
		
	
	def buildVideoBouquet(self):
		movs = Bouquet(Bouquet.TYPE_MENU, 'films')
		for x in self.currentPageIds:
			mov = Bouquet(Bouquet.TYPE_MENU, x, self.videos[x].name, self.videos[x].year) #two sort args [name, year]
			movs.append(mov)
		return movs
	
	def buildEpisodesBouquet(self, vid):
		files = Bouquet(Bouquet.TYPE_MENU, vid) 
		for x in self.videos[vid].files:
			print 'add fid', x, 'to bouquet'
			file = Bouquet(Bouquet.TYPE_SERVICE, x)
			files.append(file)
		return files

def floatConvert(s):
	return s and int(float(s)*10) or 0 


