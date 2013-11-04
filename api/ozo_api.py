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
import cookielib, urllib, urllib2 #TODO: optimize imports
from json import loads as json_loads
from datetime import datetime
from md5 import md5
from . import tdSec, secTd, setSyncTime, syncTime, EpgEntry, Channel, Timezone, APIException

# hack !
class JsonWrapper(dict):
	def find(self, key):
		if isinstance(self[key], dict):
			return JsonWrapper(self[key])
		if isinstance(self[key], list):
			return map(JsonWrapper, self[key])
		else:
			return self[key]
	def findtext(self, key):
		return unicode(self[key])
                                                                                                               
def loads(jsonstr):
	return JsonWrapper(json_loads(jsonstr))
	
class OzoAPI(AbstractAPI):
	
	iProvider = "ozo"
	NUMBER_PASS = False
	HAS_PIN = True
	
	site = "http://file-teleport.com/iptv/api/v1/json"

	def __init__(self, username, password):
		AbstractAPI.__init__(self, username, password)
		
		self.time_shift = 0
		self.time_zone = 0
		self.protect_code = ''

		self.cookiejar = cookielib.CookieJar()
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
		self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 technic-plugin-1.5'),
					('Connection', 'Close'), 
					('Accept', 'application/json, text/javascript, */*'),
					('X-Requested-With', 'XMLHttpRequest'), ('Content-Type', 'application/x-www-form-urlencoded')]
		
	def start(self):
		self.authorize()
	
	def setTimeShift(self, timeShift): #in hours #sets timezone also
		return
		params = {'var': 'time_shift',
				  'val': timeShift }
		return self.getData(self.site+"/set?"+urllib.urlencode(params), "setting time shift to %s" % timeShift)

	def authorize(self):
		self.trace("Username is "+self.username)
		self.cookiejar.clear()
		md5pass = md5(md5(self.username).hexdigest() + md5(self.password).hexdigest()).hexdigest()
		params = urllib.urlencode({"login" : self.username,
					"pass" : md5pass,
					"with_cfg" : '',
					"with_acc" : '' })
		self.trace("Authorization started (%s)" % (self.site+"/login?"+ params))
		response = self.getData(self.site+"/login?"+ params, "authorize", 1)
		
		if 'sid' in response:
			self.sid = response['sid'].encode("utf-8")
			self.SID = True
	
		if 'settings' in response:
			if 'time_shift' in response['settings']:
				self.time_shift = response['settings']['time_shift']
			if 'time_zone' in response['settings']:
				self.time_zone = response['settings']['time_zone']
				
		if 'packet_expire' in response:
			self.packet_expire = datetime.fromtimestamp(int(response['packet_expire'])) 
	 	return 0
				
	def getData(self, url, name, fromauth=None):
		if not self.SID and not fromauth:
			self.authorize()
		self.SID = False 
		self.trace("Getting %s (%s)" % (name, url))
		try:
			reply = self.opener.open(url).read()
		except:
			reply = ""
		#print reply
		try:
			json = loads(reply)
		except:
			raise APIException("Failed to parse json response")
		if 'error' in json:
			error = json['error']
			raise APIException(error['code'].encode('utf-8') + ": " + error['message'].encode('utf-8'))
		self.SID = True
		return json 

	
class Ktv(OzoAPI, AbstractStream):
	
	iName = "OzoTV"
	MODE = MODE_STREAM
	
	locked_cids = [155, 156, 157, 158, 159]
	
	def __init__(self, username, password):
		OzoAPI.__init__(self, username, password)
		AbstractStream.__init__(self)

        def epg_entry(self, e):                                                                                                               
                txt   = e['title'].encode('utf-8') + '\n' + e['info'].encode('utf-8')                                                         
                start = datetime.fromtimestamp(int(e['begin'])+ts_fix)                                                                        
                end   = datetime.fromtimestamp(int(e['end'])+ts_fix)                                                                          
                return (txt,start,end)

	def channel_day_epg(self, channel):
		if not 'epg' in channel: return
		for e in channel['epg']:
			if 'time_shift' in e: ts_fix = int(e["time_shift"])
			else: ts_fix =self.time_shift
			yield self.epg_entry(e)

	def channel_epg_current(self, channel):
		if not 'epg' in channel: return
		ch = channel['epg']
		ts_fix =self.time_shift
		if 'time_shift' in ch:
			ts_fix = int(ch["time_shift"])
		for typ in ['current', 'next']:
			if not typ in ch: continue 
			yield self.epg_entry(ch[typ])

	def setChannelsList(self):
		params = urllib.urlencode({"with_epg":''}) 
		response = self.getData(self.site+"/get_list_tv?"+params, "channels list")
		
		for group in response['groups']:
			gid = group['id']
			groupname = group['name'].encode('utf-8')
			for channel in group['channels']: 
				id = channel['id']
				name = channel['name'].encode('utf-8')
				num = channel['number'] 
				archive = ('has_archive' in channel) and (int(channel['has_archive']))
				self.channels[id] = Channel(name, groupname, num, gid, archive)
				self.channels[id].is_protected = ('protected' in channel) and (int(channel['protected']))
				for t,s,e in self.channel_epg_current(channel):
					self.channels[id].epg = EpgEntry(t, s, e)
					self.channels[id].nepg = EpgEntry(t, s, e)

	def getStreamUrl(self, cid, pin, time = None):
		params = {"cid": cid, "time_shift": self.time_shift}
		if self.channels[cid].is_protected:
			params["protect_code"] = self.protect_code
		if time:
			params["uts"] = time.strftime("%s")
		response = self.getData(self.site+"/get_url_tv?"+urllib.urlencode(params), "stream url")
		return response["url"].encode("utf-8")
	
	def getChannelsEpg(self, cids):
		response = self.getData(self.site+"/get_epg_current?"+urllib.urlencode({"cid":','.join(str(c) for c in cids)}), "getting epg of all channels")
		for prog in response['channels']:
			id = prog['id']
			for t,s,e in self.channel_epg_current(prog):
				self.channels[id].epg = EpgEntry(t, s, e)
                                self.channels[id].nepg = EpgEntry(t, s, e)
	
	def getCurrentEpg(self, cid):
		return self.getChannelsEpg([cid])
	
	def on_getDayEpg(self, id, dt):
		params = {"cid": id,
			  "from_uts": datetime(dt.year, dt.month, dt.day).strftime('%s'),
			  "hours" : 24}
		response = self.getData(self.site+"/get_epg?"+urllib.urlencode(params), "EPG for channel %s" % id)
		for channel in response['channels']:
			yield self.channel_day_epg(channel)
