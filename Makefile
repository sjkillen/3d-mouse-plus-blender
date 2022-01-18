all: 3d-mouse-plus.zip

.PHONY: 3d-mouse-plus.zip
3d-mouse-plus.zip: *.py LICENSE pywinusb
	zip -r $@ $^
