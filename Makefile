plugin_name=e2iptv
extensions_path=/usr/lib/enigma2/python/Plugins/Extensions

SOURCES := $(shell find build -name '*.py')

make_build:
	if ! test -d build; then \
		mkdir -p "build/${extensions_path}/${plugin_name}"; \
	fi

clean_build:
	if test -d build; then rm -rf build; fi

prepare_build: clean_build make_build
	cp -rf api build/${extensions_path}/${plugin_name}/
	cp *.png build/${extensions_path}/${plugin_name}/
	cp -rf DEBIAN build/

compile: $(SOURCES)
	./bin/py-compile $(SOURCES)
	rm $(SOURCES)

make_ipk:
	if ! test -d packages; \
		then mkdir packages; fi; \
	dpkg-deb -b -Zgzip build  packages;
	cd packages; \
	for file in `ls |grep deb`; do \
		mv $$file `echo $$file |sed s/deb/ipk/`; \
	done

all: prepare_build make_ipk
