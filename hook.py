#!/usr/bin/env python2
#
# TexCompleter - Semantic completer for YouCompleteMe which handles Tex files.
# Copyright (C) 2015 Till Smejkal <till.smejkal@ossmail.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import sys
from os.path import dirname

current_dir = dirname(__file__)
sys.path.append(current_dir)

from tex_completer import TexCompleter

sys.path.remove(current_dir)

def GetCompleter(user_options):
    return TexCompleter(user_options)

# vim: ft=python tw=80 expandtab tabstop=4
