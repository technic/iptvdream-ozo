pyfiles_mixtv := $(shell find -name '*.py' -type f |grep mixtv)
pyfiles_ozo := $(shell find -name '*.py' -type f |grep ozo)
pyfiles_api1 := api/api1.py

controldir_mixtv = DEBIAN-mixtv
controldir_ozo = DEBIAN-ozo
controldir_api1 = DEBIAN-api1

scanver_file_ozo := api/api1.py
scanver_file_mixtv := api/api1.py
scanver_file_api1 := api/api1.py

datafiles_ozo = OzoMovies.png OzoTV.png
datafiles_mixtv = MIXTV.png MIXTVMovies.png

all: ipk

src/%:
	ln -s . src

include ../iptvdream.mk
$(call doipk,ozo)
$(call doipk,mixtv)
$(call doipk,api1)
