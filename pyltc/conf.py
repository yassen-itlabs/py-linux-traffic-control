"""
Default settings for the PyLTC framework.

"""

__version__ = (0, 4, 7)
__build__ = 84
__maintainer__ = "Yassen Damyanov <yd-at-itlabs.bg>"


from os.path import abspath, normpath, dirname, join as pjoin
HOME_DIR = pjoin(normpath(abspath(dirname(__file__))), "..")

#: paths to look up for a profile configuration file if none is given on the command line
CONFIG_PATHS = (
    './pyltc.profiles',
    '/etc/pyltc.profiles',
)

#: paths to load setup processing plugins from
PLUGINS_PATHS = (
    pjoin(HOME_DIR, 'plugins'),
)
