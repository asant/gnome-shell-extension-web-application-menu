include $(top_srcdir)/include.mk

dist_extension_DATA = extension.js webappmenu-setup.py
nodist_extension_DATA = metadata.json settings.json

metadata.json: metadata.json.in $(top_builddir)/config.status
	$(AM_V_GEN) sed \
		-e "s|[@]compatible_shell_versions@|$(compatible_shell_versions)|" \
		-e "s|[@]uuid@|$(uuid)|" \
		-e "s|[@]extension_url@|$(extension_url)|" \
		-e "s|[@]extension_version@|$(extension_version)|" \
		$< > $@

