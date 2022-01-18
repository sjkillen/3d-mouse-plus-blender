all: 3d-mouse-plus.zip

.PHONY: 3d-mouse-plus.zip
3d-mouse-plus.zip: *.py LICENSE pywinusb
	rm -f $@
	mkdir -p 3d-mouse-plus
	cp -a $^ 3d-mouse-plus/
	zip -r $@ 3d-mouse-plus/
	rm -rf 3d-mouse-plus
