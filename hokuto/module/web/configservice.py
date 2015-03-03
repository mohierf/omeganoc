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

""" Contains pages and web services used to manipulate shinken configuration files """

import os

from pynag.Utils import paths
from pynag.Parsers import config

from flask import jsonify, render_template, abort
from flask.ext.login import login_required
from wtforms import Form, TextField, SelectField, SelectMultipleField, TextAreaField,  validators
from wtforms.fields.html5 import IntegerField, URLField
from werkzeug.contrib.cache import SimpleCache
from shinken.property import none_object
import shinken.objects

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

def _parsetype(type):
    """ 
    Checks if the specified type name is a template, and returns the actual
    nagios/shinken data type and a boolean telling if it was a template.
    
    For example if you pass 'hosttemplate' you'll get ('host', True)
    But if you pass 'host' you'll get ('host', False)
    """
    istemplate = False
    if type.endswith('s'):
        type = type[:-1] # Remove the trailing 's'
    if type.endswith('template'):
        istemplate = True
        type = type[:-8] # Remove the trailing 'template'
    return (type, istemplate)
        
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
    (type, istemplate) = _parsetype(type)
    
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

@app.route('/config/<type>/<id>')
@login_required
def config_details(type, id):
    print 'lel'
    # try to get the target element
    (type, istemplate) = _parsetype(type)
    print type, istemplate
    if type not in _typekeys:
        abort(404) # Unsupported type
    
    conf = _getconf()
    typekey = 'all_' + type
    if typekey not in conf.data:
        abort(404) # No element of this type
    primkey = _typekeys[type]
    target = next((e for e in conf.data[typekey] if primkey in e and e[primkey] == id), None)
    if target is None:
        abort(404) # Unknown id
    
    form = HostForm()
    _fillform(form, target)
    _annotateform(form, target)
    
    return render_template('config/details.html', type=type, id=id, data=_normalizestrings(target), form=form)
    
@app.route('/config/canwrite')
@login_required
def config_can_edit():
    confpath = paths.find_main_configuration_file()
    result = os.access(confpath, os.W_OK)
    return jsonify({'success': True, 'data':result})

# #########################################################################################################
# Form tools

def _fillform(form, data):
    for k,v in data['meta']['defined_attributes'].iteritems():
        field = getattr(form, k, None)
        if field is not None:
            print 'Setting field {0} to {1}'.format(k, v)
            if isinstance(field, SelectMultipleField):
                field.process(None, v.split(','))
            else:
                field.process(None, v)
                
def _annotateform(form, data):
    typedata = getattr(shinken.objects, data['meta']['object_type'].title(), None)
    if typedata is None:
        return
    for field in form:
        propdata = None
        if field.name in typedata.properties:
            propdata = typedata.properties[field.name]
        # Is the value inherited ?
        if field.name in data['meta']['inherited_attributes']:
            desc = _createannotation(data['meta']['inherited_attributes'][field.name], True)
            if desc is not None:
                field.description = desc
        elif propdata is not None:
            if propdata.default != none_object:
                desc = _createannotation(propdata.default, False)
                if desc is not None:
                    field.description = desc

def _createannotation(value, inherited):
    """ 
    Generates a string that describes the default value of a property 
    
    value contains the default value applied
    inherited tells if the default value is applied because it's inherited
    (True) or just because no value is available (False)
    """
    empty = False
    if value is None:
        empty = True
    elif hasattr(value, '__len__') and len(value) == 0:
        empty = True
    
    if empty:
        if inherited:
            return 'Default value: empty (inherited)'
        else:
            return None
    
    if isinstance(value, list):
        value = ', '.join(value)
        
    if isinstance(value, bool):
        if value:
            value = 'Yes'
        else:
            value = 'No'
        
    value = 'Default: {0}'.format(value)
    if inherited:
        value = value + ' (inherited)'
    return value
            
def _listobjects(type, key = None):
    if key is None:
        key = type + '_name'
    conf = _getconf()
    typekey = 'all_' + type
    if typekey in conf.data:
        result = [i[key] for i in conf.data[typekey] if key in i]
        result.sort()
        return result
    else:
        return []

def _listobjects_choices(type, addempty = False, key = None):
    """ Gets a list from _listobjects and formats it so it can work with a SelectField """
    data = _listobjects(type, key)
    data = [(i,i) for i in data]
    if addempty:
        data.insert(0, ('', '<unspecified>'))
    return data
    
def _listboolean_choices():
    return [('', '<unspecified>'), ('y', 'Yes'), ('n', 'No')]
    
# #########################################################################################################
# Forms

class HostForm(Form):
    #Description
    host_name = TextField('Host name')
    alias = TextField('Alias')
    display_name = TextField('Display name')
    address = TextField('Address')
    notes = TextAreaField('Notes')
    notes_url = URLField('Notes URL')
    action_url = URLField('Action URL')
    
    #Structure
    parents = SelectMultipleField('Parents', choices=_listobjects_choices('host'))
    hostgroups = SelectMultipleField('Host groups', choices=_listobjects_choices('hostgroup'))
    
    #Checking
    check_command = SelectField('Check command', choices=_listobjects_choices('command', True))
    initial_state = SelectField('Initial state', choices=[('', '<unspecified>'), ('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])
    max_check_attempts = IntegerField('Maximum check attempts', validators=[validators.Optional(), validators.NumberRange(0)])
    check_interval = IntegerField('Check interval')
    retry_interval = IntegerField('Retry interval')
    active_checks_enabled = SelectField('Enable active notifications', choices=_listboolean_choices())
    passive_checks_enabled = SelectField('Enable passive notifications', choices=_listboolean_choices())
    check_period = SelectField('Check command', choices=_listobjects_choices('timeperiod', True))
    obsess_over_host = SelectField('Obsess over host', choices=_listboolean_choices())
    check_freshness = SelectField('Check freshness', choices=_listboolean_choices())
    freshness_threshold = IntegerField('Freshness threshold')
    
    #Status management
    event_handler = SelectField('Event handler', choices=_listobjects_choices('command', True))
    event_handler_enabled = SelectField('Event handler enabled', choices=_listboolean_choices())
    low_flap_threshold = IntegerField('Low flap threshold')
    high_flap_threshold = IntegerField('High flap threshold')
    flap_detection_enabled = SelectField('Flap detection enabled', choices=_listboolean_choices())
    flap_detection_options = SelectMultipleField('Flap detection options', choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])
    retain_status_information = SelectField('Retain status info', choices=_listboolean_choices())
    retain_nonstatus_information = SelectField('Retain non-status info', choices=_listboolean_choices())
    
    #Notifications
    notifications_enabled = SelectField('Enable notifications', choices=_listboolean_choices())
    contacts = SelectMultipleField('Contacts', choices=_listobjects_choices('contact'))
    contact_groups = SelectMultipleField('Contact groups', choices=_listobjects_choices('contactgroup'))
    notification_interval = IntegerField('Notification interval')
    first_notification_delay = IntegerField('First notification delay')
    notification_period = SelectField('Notification period', choices=_listobjects_choices('timeperiod', True))
    notification_options = SelectMultipleField('Notification options', choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])
    
    # Misc.
    process_perf_data = SelectField('Process perf data', choices=_listboolean_choices())
    stalking_options = SelectMultipleField('Stalking options', choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])