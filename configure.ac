AC_PREREQ(2.63)
AC_INIT([gnome-shell-extension-web-application-menu],[14],[https://github.com/asant/gnome-shell-extension-web-application-menu])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_AUX_DIR([config])
AC_PREFIX_PROGRAM(gnome-shell)

AM_INIT_AUTOMAKE([1.10 dist-bzip2 no-dist-gzip foreign tar-ustar])

m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])

GETTEXT_PACKAGE=web-application-menu
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE",
                   [The prefix for our gettext translation domains.])
IT_PROG_INTLTOOL(0.26)

PKG_PROG_PKG_CONFIG([0.22])

AC_CONFIG_FILES([
  src/Makefile
  Makefile
  po/Makefile.in
])
AC_OUTPUT

