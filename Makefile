PLUGINS = $(wildcard *.py)

all:
	@echo "Usage: make install"

install:
	mkdir -p "$$HOME/.osc-plugins"
	cp $(PLUGINS) "$$HOME/.osc-plugins"
