include $(top_srcdir)/extension.mk

metadata.json: metadata.json.in $(top_builddir)/config.status
	$(AM_V_GEN) sed \
		-e "s|[@]compatible_shell_versions@|$(compatible_shell_versions)|" \
		-e "s|[@]uuid@|$(uuid)|" \
		-e "s|[@]extension_url@|$(extension_url)|" \
		-e "s|[@]extension_version@|$(extension_version)|" \
		-e "s|[@]system_locale_dir@|$(localedir)|" \
		-e "s|[@]gettext_domain@|$(extension_name)|" \
		$< > $@

CLEANFILES = metadata.json

