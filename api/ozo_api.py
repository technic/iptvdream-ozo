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

from abstract_api import MODE_STREAM, AbstractAPI, AbstractStream
from datetime import datetime
from md5 import md5
from . import tdSec, secTd, setSyncTime, syncTime, Timezone, APIException
	
class OzoAPI(AbstractAPI):
	
	iProvider = "ozo"
	NUMBER_PASS = False
	
	site = "http://core.ozo.tv/iptv/api/v1/json"

	def __init__(self, username, password):
		AbstractAPI.__init__(self, username, password)		
		self.time_shift = 0
		self.time_zone = 0
		self.servertime = 0
		
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
			if 'time_shift' in response['settings']:
				self.time_shift = response['settings']['time_shift']
			if 'time_zone' in response['settings']:
				self.time_zone = response['settings']['time_zone']
				
		if 'packet_expire' in response:
			self.packet_expire = datetime.fromtimestamp(int(response['packet_expire'])) 
		if 'servertime' in response:
			self.servertime = response['servertime']
	 	return params
				
	def getChannelsData(self):
		params = {"with_epg":'true', 'servertime':self.servertime}
		return self.getJsonData(self.site+"/get_list_tv?", params, "channels list")

	def getUrlData(self, cid, pin, time):
		params = {"cid": cid, "time_shift": self.time_shift, 'servertime':self.servertime}
		if self.channels[cid].is_protected and pin:
			params["protect_code"] = pin
		if time:
			params["uts"] = time.strftime("%s")
		return self.getJsonData(self.site+"/get_url_tv?", params, "stream url")

	
class e2iptv(OzoAPI, AbstractStream):
	
	iName = "OzoTV"
	NEXT_API = "OzoMovies"
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
			group_name = group['name'].encode('utf-8')
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
		response = self.getJsonData(self.site+"/get_epg_current?", {"cid": cstr}, "epg of channels: " + cstr)
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
			  "hours" : 24}
		response = self.getJsonData(self.site+"/get_epg?", params, "EPG for channel %s" % id)
		if 'servertime' in response:
			self.servertime = response['servertime']
		for channel in response['channels']:
			return self.channel_day_epg(channel)
