ACLOCAL_AMFLAGS = -I m4 ${ACLOCAL_FLAGS}

SUBDIRS = src po

include include.mk

install-exec-hook:
	chmod a+x $(DESTDIR)$(extensiondir)/webappmenu-setup.py

zip-file: all
	rm -fR $(builddir)/_build
	rm -fR $(builddir)/zip-files
	$(MKDIR_P) $(builddir)/_build; \
	$(MKDIR_P) $(builddir)/zip-files; \
	$(MAKE) install DESTDIR="$(abs_builddir)/_build"; \
	cp "$(srcdir)/AUTHORS" -t $(builddir)/_build$(extensiondir); \
	cp "$(srcdir)/COPYING" -t $(builddir)/_build$(extensiondir); \
	cp "$(srcdir)/README" -t $(builddir)/_build$(extensiondir); \
	[ -d "$(builddir)/_build$(localedir)" ] && cp -a "$(builddir)/_build$(localedir)" -t $(builddir)/_build$(extensiondir); \
	(cd "$(builddir)/_build$(extensiondir)"; \
	 zip -qr "$(abs_builddir)/zip-files/gnome-shell-extension-$(extension_name)" .; \
	); \
	rm -fR $(builddir)/_build

localprefix = $(HOME)/.local/share/gnome-shell/extensions

local-install: zip-file
	$(MKDIR_P) "$(abs_builddir)/_local-install"; \
	pushd "$(abs_builddir)/_local-install"; \
	unzip -o -q "$(abs_builddir)/zip-files/gnome-shell-extension-$(extension_name)"; \
	popd; \
	if [ -d "$(localprefix)/${uuid}" ]; then \
	if [ -f "$(localprefix)/${uuid}/settings.json" ]; then \
	cp --remove-destination "$(localprefix)/${uuid}/settings.json" -t "$(abs_builddir)/_local-install"; \
	fi; \
	rm -fR "$(localprefix)/${uuid}"; \
	fi; \
	$(MKDIR_P) $(localprefix)/${uuid}; \
	cp -a --remove-destination "$(abs_builddir)/_local-install"/* -t "$(localprefix)/${uuid}"; \
	rm -rf "$(abs_builddir)/_local-install"

clean-local:
	-rm -rf zip-files ; \
	rm -f po/*.gmo

