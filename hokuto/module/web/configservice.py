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

from flask import jsonify, render_template, abort
from flask.ext.login import login_required
from werkzeug.contrib.cache import SimpleCache

from . import app, cache

_typekeys = {
    'host': 'host_name',
    'service': 'service_description',
    'hostgroup': 'hostgroup_name',
    'servicegroup': 'servicegroup_name',
    'contact': 'contact_name',
    'contactgroup': 'contactgroup_name',
    'timeperiod': 'timeperiod_name',
    'command': 'command_name',
}

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
            
@app.route('/config/list/<type>')
@login_required
def conf_getdatalist(type):
    """ Returns a JSON object containing all the data for objects of the specified type """
    istemplate = False
    if type.endswith('templates'):
        istemplate = True
        type = type[:-9]
    else:
        type = type[:-1] # Just remove the trailing s
        
    if type not in _typekeys:
        return jsonify({'success': False, 'errormessage': 'Unknown object type'}), 404
    key = _typekeys[type]
    if istemplate:
        key = 'name'
    conf = _getconf()
    datakey = 'all_' + type
    if datakey in conf.data:
        data = _normalizestrings([i for i in conf['all_' + type] if key in i])
    else:
        # If the key does not exist, it's usually because no elements of that type were found in the config files
        data = []
    return jsonify({'success': True, 'data': data})
    
            
@app.route('/config')
@login_required
def config_list():
    return render_template('config/list.html')

@app.route('/config/canwrite')
@login_required
def config_can_edit():
    confpath = paths.find_main_configuration_file()
    result = os.access(confpath, os.W_OK)
    return jsonify({'success': True, 'data':result})
