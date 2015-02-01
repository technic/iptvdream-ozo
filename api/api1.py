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

VERSION = "2.3.1"

from abstract_api import MODE_STREAM, MODE_VIDEOS, AbstractAPI, AbstractStream
from datetime import datetime
from md5 import md5
from . import tdSec, secTd, setSyncTime, syncTime, Timezone, APIException, Bouquet, Video, unescapeEntities


class OzoAPI(AbstractAPI):
	
	iProvider = "ozo"
	NUMBER_PASS = False
	
	site = "http://core.ozo.tv/iptv/api/v1/json"

	def __init__(self, username, password):
		AbstractAPI.__init__(self, username, password, VERSION)
		self.time_shift = 0
		self.time_zone = 0
		self.servertime = 0
		self.settings = {}
		
	def start(self):
		self.authorize()

	def authorize(self, params=None):
		self.trace("Username is "+self.username)
		md5pass = md5(md5(self.username).hexdigest() + md5(self.password).hexdigest()).hexdigest()
		params = {"login":self.username, "pass":md5pass, "with_cfg":'', "with_acc":'', "servertime":self.servertime }
		response = self.getJsonData(self.site+"/login?", params, "authorize", 1)
		
		if 'sid' in response:
			self.sid = response['sid'].encode("utf-8")
	
		if 'settings' in response:
			try:
				self.parseSettings(response['settings'])
			except:
				pass
			if 'time_shift' in response['settings']:
				self.time_shift = int(response['settings']['time_shift'])
			if 'time_zone' in response['settings']:
				self.time_zone = int(response['settings']['time_zone'])
				
		for s in response['account']['subscriptions']:
			if 'end_date' in s:
				if self.packet_expire:
					self.packet_expire += '/'+s['end_date'].encode("utf-8") 
				else:
					self.packet_expire = s['end_date'].encode("utf-8")
		if 'servertime' in response:
			self.servertime = response['servertime']
	 	return params
				
	def parseSettings(self, settings):
		self.settings['Language']           = {'id':'interface_lng', 'value':settings['interface_lng'].encode('utf-8'), 'vallist':['ru','de','ua','en']}
		self.settings['Cache size(seconds)']= {'id':'stb_buffer', 'value':int(settings['stb_buffer']), 'vallist':range(0,30)}
		self.settings['Timeshift']          = {'id':'time_shift', 'value':int(settings['time_shift']), 'vallist':range(0,24)}

		media_servers = [(s['id'].encode('utf-8'), s['title'].encode('utf-8')) for s in settings['media_servers']]
		self.settings['Stream server']={'id':'media_server_id', 'value': settings['media_server_id'], 'vallist':media_servers}
	def getChannelsData(self):
		params = {"with_epg":'true', "time_shift": self.time_shift}
		return self.getJsonData(self.site+"/get_list_tv?", params, "channels list")

	def getUrlData(self, cid, pin, time):
		params = {"cid": cid, "time_shift": self.time_shift}
		if self.channels[cid].is_protected and pin:
			params["protect_code"] = pin
		if time:
			params["uts"] = time.strftime("%s")
		return self.getJsonData(self.site+"/get_url_tv?", params, "stream url")

	
class OzoStream(OzoAPI, AbstractStream):
	
	MODE = MODE_STREAM
	HAS_PIN = True
	
	def __init__(self, username, password):
		OzoAPI.__init__(self, username, password)
		AbstractStream.__init__(self)

	def epg_entry(self, e, ts_fix):
		txt   = e['title'].encode('utf-8') + '\n' + e['info'].encode('utf-8')
		start = datetime.fromtimestamp(int(e['begin'])+ts_fix)
		end   = datetime.fromtimestamp(int(e['end'])+ts_fix)
		return ({"text":txt,"start":start,"end":end})

	def channel_day_epg(self, channel):
		if not 'epg' in channel: return
		for e in channel['epg']:
			if 'time_shift' in e: ts_fix = int(e["time_shift"])
			else: ts_fix =self.time_shift
			if not (('begin' in e) and e['begin'] and ('end' in e) and e['end']): continue
			yield self.epg_entry(e, ts_fix)

	def on_channelEpgCurrent(self, channel):
		if not 'epg' in channel: return
		ch = channel['epg']
		if 'time_shift' in ch: ts_fix = int(ch["time_shift"])
		else: ts_fix =self.time_shift
		for typ in ['current', 'next']:
			if not typ in ch: continue 
			e = ch[typ]
			if not (('begin' in e) and e['begin'] and ('end' in e) and e['end']): continue
			yield self.epg_entry(e, ts_fix)

	def on_setChannelsList(self):
		channelsData = self.getChannelsData()

		if 'servertime' in channelsData:
			self.servertime = channelsData['servertime']
		
		for group in channelsData['groups']:
			group_id = group['id']
			group_name = group['user_title'].encode('utf-8')
			for channel in group['channels']: 
				id          = channel['id']
				name        = channel['name'].encode('utf-8')
				number      = channel['number'] 
				has_archive = ('has_archive' in channel) and (int(channel['has_archive']))
				is_protected = ('protected' in channel) and (int(channel['protected']))
				yield ({"id":id,
					"group_id":group_id,
					"group_name":group_name,
					"name":name,
					"number":number,
					"has_archive":has_archive,
					"is_protected":is_protected,
					"epg_data_opaque":channel})

	def on_getStreamUrl(self, cid, pin, time = None):
		response = self.getUrlData(cid, pin, time)
		if 'servertime' in response:
			self.servertime = response['servertime']
		return response["url"].encode("utf-8")
	
	def on_getChannelsEpg(self, cids):
		cstr = ','.join(str(c) for c in cids)
		params = {"cid": cstr, "time_shift": self.time_shift}
		response = self.getJsonData(self.site+"/get_epg_current?", params, "epg of channels: " + cstr)
		if 'servertime' in response:
			self.servertime = response['servertime']
		for prog in response['channels']:
			id = prog['id']
			for e in self.on_channelEpgCurrent({'epg':prog}):
				e['id']=id
				yield e
	
	def on_getCurrentEpg(self, cid):
		return self.on_getChannelsEpg([cid])
	
	def on_getDayEpg(self, id, dt):
		params = {"cid": id,
			  "from_uts": datetime(dt.year, dt.month, dt.day).strftime('%s'),
              "time_shift": self.time_shift, 'servertime':self.servertime,			
			  "hours" : 24}
		response = self.getJsonData(self.site+"/get_epg?", params, "EPG for channel %s" % id)
		if 'servertime' in response:
			self.servertime = response['servertime']
		for channel in response['channels']:
			return self.channel_day_epg(channel)
	def getSettings(self):
		return self.settings

	def pushSettings(self, sett):
		for s in sett:
			params = {'var':s[0]['id'],'val':s[1]}
			response = self.getJsonData(self.site+"/set?", params, "Push setting [%s] new value." % s[0]['id'])
			s[0]['value'] = s[1]


class OzoVideos(OzoAPI):
	
	MODE = MODE_VIDEOS
	
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
