
def version_from_file(filename):
    try:
        f = open(filename)
    except EnvironmentError:
        return None
    for line in f.readlines():
        mo = re.match("__version__ = '([^']+)'", line)
        if mo:
            ver = mo.group(1)
            return ver
    return None

def version_from_parentdir(tag_prefix, parentdir_prefix, verbose):
    # try a couple different things to handle py2exe, bbfreeze, and
    # non-CPython implementations. Since this code lives in versioneer.py, we
    # either expect __file__ to be versioneer.py (kept in the root of the
    # source tree), or for sys.argv[0] to be setup.py (also in the root),
    # such that its parent is the root of the unpacked tarball, which
    # conventionally includes both a project name and a version string.
    try:
        me = __file__
    except NameError:
        me = sys.argv[0]
    me = os.path.abspath(me)
    dirname = os.path.basename(os.path.dirname(me))
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print "dirname '%s' doesn't start with prefix '%s'" % \
                  (dirname, parentdir_prefix)
        return None
    return dirname[len(parentdir_prefix):]

def write_to_version_file(filename, ver):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % ver)
    f.close()
    print "set %s to '%s'" % (filename, ver)

def get_expanded_variable(versionfile_source):
    # the code embedded in _version.py can just fetch the value of this
    # variable. We don't want to import _version.py, so we do it with a
    # regexp instead
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("verstr ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    return mo.group(1)
    except EnvironmentError:
        pass
    return None

def get_best_version(versionfile, tag_prefix, parentdir_prefix,
                     source_root=None, default=None, verbose=False):
    # extract version from first of: 'git describe', _version.py, parentdir.
    # This is meant to work for developers, for users of a tarball created by
    # 'setup.py sdist', and for users of a tarball/zipball created by 'git
    # archive' or github's download-from-tag feature.

    ver = version_from_vcs(tag_prefix, verbose)
    if ver is not None:
        if verbose: print "got version from git"
        return ver

    verstr = get_expanded_variable(versionfile_source)
    if verstr:
        ver = version_from_expanded_variable(verstr, tag_prefix)
        if ver is not None:
            if verbose: print "got version from expanded variable"
            return ver

    ver = version_from_file(versionfile)
    if ver is not None:
        if verbose: print "got version from file %s" % versionfile
        return ver

    ver = version_from_parentdir(tag_prefix, parentdir_prefix, verbose)
    if ver is not None:
        if verbose: print "got version from parentdir"
        return ver

    ver = default
    if ver is not None:
        if verbose: print "got version from default"
        return ver

    raise NoVersionError("Unable to compute version at all")

def get_version(verbose=False):
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    return get_best_version(versionfile_source, tag_prefix, parentdir_prefix,
                            verbose=verbose)

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print "Version is currently:", ver


class cmd_build(_build):
    def run(self):
        ver = get_version(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print "UPDATING", target_versionfile
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % ver)
        f.close()

class cmd_sdist(_sdist):
    def run(self):
        ver = get_version(verbose=True)
        self._versioneer_generated_version = ver
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = ver
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print "UPDATING", target_versionfile
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_version)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_version
__version__ = get_version()
del get_version

"""

class cmd_update_files(Command):
    description = "modify __init__.py and create _version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        print " creating %s" % versionfile_source
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$", "TAG_PREFIX": tag_prefix})
        f.close()
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print " appending to %s" % ipy
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print " %s unmodified" % ipy
        do_vcs_install(versionfile_source, ipy)

def get_cmdclass():
    return {'version': cmd_version,
            'update_files': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }
