#!/usr/bin/env python
#
# This file is part of Omega Noc
# Copyright Omega Noc (C) 2015 Omega Cube and contributors
# Xavier Roger-Machart, xrm@omegacube.fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Contains web services used to manipulate shinken configuration files """

# Operations :
# - canedit (optionnal path param) - determines if the shinken main conf (/etc/shinken/shinken.cfg) can be written

import os

from pynag.Utils import paths
from pynag.Parsers import config

from flask import jsonify, render_template
from flask.ext.login import login_required
from werkzeug.contrib.cache import SimpleCache

from . import app, cache

def _getconf():
    conf = cache.get('nag_conf')
    if conf is None:
        # No conf in cache; load it
        conf = config() # Let pynag find out the configuration path by itself
        conf.parse()
        cache.set('nag_conf', conf, timeout=60) #TODO : Configure cache timeout
    return conf

def _readStr(source, attr, default = None):
    """ Reads a string from a distionnary value and returns it as unicode, making sure we get no encoding errors """
    if attr in source:
        return unicode(source[attr], errors='replace')
    else:
        return default
        
def _normalizestrings(data):
    """ 
    Recursively checks all the strings in the provided dict to make sure they only contain valid utf-8 characters.
    We do this to avoid errors during serialisation and transmission of the data with JSON.
    """
    if isinstance(data, str):
        # Non unicode strings : turn to unicode, secure invalid chars
        return unicode(data, errors='replace')
    elif isinstance(data, unicode):
        # Already unicode strings : return as-is
        return value
    elif isinstance(data, list):
        # Lists : check each element
        for val in xrange(0, len(data)):
            data[val] = _normalizestrings(data[val])
        return data
    elif isinstance(data, dict):
        # Dicts : Check each element
        for k, v in data.iteritems():
            data[k] = _normalizestrings(v)
        return data
    else:
        #Everything else : return as-is
        return data
            
            
    
@app.route('/config/list')
@login_required
def config_list():
    return render_template('config/list.html')

@app.route('/config/canwrite')
@login_required
def config_can_edit():
    confpath = paths.find_main_configuration_file()
    result = os.access(confpath, os.W_OK)
    return jsonify({'result':result})

@app.route('/config/hosts')
@login_required
def config_get_hosts():
    conf = _getconf()
    #data = [{'name':_readStr(h, 'host_name'), 'alias':_readStr(h, 'alias')} for h in conf['all_host'] if 'host_name' in h]
    data = _normalizestrings([h for h in conf['all_host'] if 'host_name' in h])
    return jsonify({'data':data})