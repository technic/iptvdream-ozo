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

from api1 import OzoVideos

class e2iptv(OzoVideos):
	iProvider = "ozo"
	site = "http://core.ozo.tv/iptv/api/v1/json"
	iName = "OzoMovies"
	NEXT_API = "OzoTV"
