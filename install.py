#
#    Copyright (c) 2026 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Installer for the WLK importer."""

from io import StringIO

import configobj
from weecfg.extension import ExtensionInstaller

CONFIG = """
##############################################################################

# Pseudo-driver, used to import WLK files

[WLK]

    # Replace with your path to the .wlk files. You can use wildcards, 
    # environment variables, and '~'.
    wlk_files = ~/path-to-wlk/*.wlk
    
    driver = user.import-wlk
"""

wlk_dict = configobj.ConfigObj(StringIO(CONFIG))


def loader():
    return WLKInstaller()


class WLKInstaller(ExtensionInstaller):
    def __init__(self):
        super(WLKInstaller, self).__init__(
            version="1.3",
            name='import-wlk',
            description='Pseudo-driver for importing WLK files',
            author="Thomas Keffer",
            author_email="tkeffer@gmail.com",
            config=wlk_dict,
            files=[('bin/user', ['bin/user/import-wlk.py',])]
        )
