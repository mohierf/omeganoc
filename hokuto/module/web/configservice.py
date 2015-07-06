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

from pynag.Parsers import config

from flask import jsonify, render_template, abort, request
from flask.ext.login import login_required
from wtforms import Form, TextField, SelectField, SelectMultipleField, TextAreaField, SelectFieldBase, validators
from wtforms.fields.html5 import IntegerField, URLField
from werkzeug.contrib.cache import SimpleCache
from shinken.property import none_object
import shinken.objects
from shinken.objects.config import Config
from shinken.property import BoolProp, PythonizeError

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
        return data
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

def _get_details(objtype, istemplate, objid, formtype, targetfinder = None):
    conf = _getconf()
    if not targetfinder:
        typekey = 'all_' + objtype
        if typekey not in conf.data:
            return 'ELEMENT TYPE NOT FOUND',404 # No element of this type
        if istemplate:
            primkey = 'name'
        else:
            primkey = _typekeys[objtype]
        target = next((e for e in conf.data[typekey] if primkey in e and e[primkey] == objid), None)
    else:
        target = targetfinder(conf, istemplate)
    if target is None:
        return 'NO TARGET', 404
        #abort(404)


    form = formtype(request.form)
    _annotateform(form, target)
    if request.method == 'POST':
        print 'iz POST!'
        if form.validate():
            # Save !
            _save_existing(conf, target, form, False)
        else:
            print 'iz not valid :('

    else: #GET
        # Fill the form with the data from the configuration file
        _fillform(form, target)
    return render_template('config/details-{0}.html'.format(objtype), type=objtype, id=objid, data=_normalizestrings(target), form=form)
    
@app.route('/config/list/<type>')
@login_required
def conf_getdatalist(type):
    """ Returns a JSON object containing all the data for objects of the specified type """
    (type, istemplate) = _parsetype(type)

    print 'Getting list for ', type, istemplate

    if type not in _typekeys:
        return jsonify({'success': False, 'errormessage': 'Unknown object type'}), 404
    key = _typekeys[type]
    if istemplate:
        key = 'name'
    print 'Key is', key
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

#hosts
@app.route('/config/host/<objid>', methods=['GET', 'POST'])
@login_required
def host_details(objid):
    return _get_details('host', False, objid, HostForm)

@app.route('/config/hosttemplate/<objid>', methods=['GET', 'POST'])
@login_required
def hosttemplate_details(objid):
    return _get_details('host', True, objid, HostForm)

#hostgroup
@app.route('/config/hostgroup/<objid>', methods=['GET', 'POST'])
@login_required
def hostgroup_details(objid):
    return _get_details('hostgroup', False, objid, HostGroupForm)

@app.route('/config/hostgrouptemplate/<objid>', methods=['GET', 'POST'])
@login_required
def hostgrouptemplate_details(objid):
    return _get_details('hostgroup', True, objid, HostGroupForm)

#services
@app.route('/config/service/<objid>/<containers>', methods=['GET', 'POST'])
@login_required
def service_details(objid, containers):
    """
    Shows the details page for a service. The service to show is specified with *objid* and *containers*:
    - *objid* contains the service_description
    - *containers* contains the host and hostgroup, concatenated together. The hosts are prefixed with $ and hostgroups are prefixed with +
    """
    # Containers mandatory
    if len(containers) == 0:
        abort(404)

    def searchservice(conf, istemplate):
        return _searchservice(conf, istemplate, objid, containers)

    return _get_details('service', False, objid + '/' + containers, ServiceForm, searchservice)

@app.route('/config/servicetemplate/<objid>', methods=['GET', 'POST'], defaults={'containers': ''})
@app.route('/config/servicetemplate/<objid>/<containers>', methods=['GET', 'POST'])
@login_required
def servicetemplate_details(objid, containers):
    print 'Gimme the template'
    # Containers may be empty for templates
    def searchservice(conf, istemplate):
        return _searchservice(conf, istemplate, objid, containers)

    return _get_details('service', True, objid + '/' + containers, ServiceForm, searchservice)

def _searchservice(conf, istemplate, objid, containers):
    ihost = -1
    ihostgroup = -1
    try:
        ihost = containers.index('$')
    except ValueError:
        pass
    try:
        ihostgroup = containers.index('+')
    except ValueError:
        pass

    service_key = 'service_description'
    if istemplate:
        service_key = 'name'

    host = None
    hostgroup = None
    if ihost >= 0:
        if ihostgroup >= 0:
            if ihost > ihostgroup:
                hostgroup = containers[ihostgroup+1:ihost-1]
                host = containers[ihost+1:]
            else:
                host = containers[ihost+1:ihostgroup-1]
                hostgroup = containers[ihostgroup+1:]
            target = next((e for e in conf.data['all_service'] if service_key in e and e[service_key] == objid and
                                                            'host_name' in e and e['host_name'] == host and
                                                            'hostgroup_name' in e and e['hostgroup_name'] == hostgroup), None)

        else:
            host = containers[ihost+1:]
            target = next((e for e in conf.data['all_service'] if service_key in e and e[service_key] == objid and
                                                            'host_name' in e and e['host_name'] == host), None)
    else:
        if ihostgroup >= 0:
            hostgroup = containers[ihostgroup+1:]
            print 'Getting it with hostgroup ', hostgroup
            target = next((e for e in conf.data['all_service'] if service_key in e and e[service_key] == objid and
                                                            'hostgroup_name' in e and e['hostgroup_name'] == hostgroup), None)
        else:
            print 'Getting a template', service_key, objid
            target = next((e for e in conf.data['all_service'] if service_key in e and e[service_key] == objid), None)
            print target
    if target is None:
        abort(404)
    return target



#services group
@app.route('/config/servicegroup/<objectid>', methods=['GET', 'POST'])
@login_required
def servicegroup_details(objectid):
    return _get_details('servicegroup', False, objectid, ServiceGroupForm)

@app.route('/config/servicegrouptemplate/<objid>', methods=['GET', 'POST'])
@login_required
def servicegrouptemplate_details(objid):
    return _get_details('servicegroup', True, objid, ServiceGroupForm)


#contacts
@app.route('/config/contact/<contactid>', methods=['GET', 'POST'])
@login_required
def contact_details(contactid):
    return _get_details('contact', False, contactid, ContactForm)

@app.route('/config/contacttemplate/<objid>', methods=['GET', 'POST'])
@login_required
def contacttemplate_details(objid):
    return _get_details('contact', True, objid, ContactForm)

#contacts group
@app.route('/config/contactgroup/<objectid>', methods=['GET', 'POST'])
@login_required
def contactgroup_details(objectid):
    return _get_details('contactgroup', False, objectid, ContactGroupForm)

@app.route('/config/contactgrouptemplate/<objid>', methods=['GET', 'POST'])
@login_required
def contactgrouptemplate_details(objid):
    return _get_details('contactgroup', True, objid, ContactGroupForm)

#time periods

#commands

# def check_config(confpath):
    # conf = Config()
    # buf = conf.read_config(confpath)
    # raw_objects = conf.read_config_buf(buf)
    # conf.create_objects(raw_objects)
    # # Checkpoint
    # if not conf.is_correct:
        # return False

    # conf.linkify_templates()
    # conf.apply_inheritance()
    # conf.explode()
    # conf.apply_implicit_inheritance()
    # conf.fill_default()
    # conf.remove_templates()
    # conf.compute_hash()
    # conf.override_properties()
    # conf.linkify()
    # conf.apply_dependencies()
    # conf.hack_old_nagios_parameters()
    # #conf.warn_about_unmanaged_parameters()
    # conf.explode_global_conf()
    # conf.propagate_timezone_option()
    # conf.create_business_rules()
    # conf.create_business_rules_dependencies()
    # #conf.notice_about_useless_parameters()
    # conf.is_correct()
    # #conf.clean() # Not need to clean since we won't use the conf anyway

    # if not conf.conf_is_correct:
        # return False
    # return True

def _save_existing(conf, data, form, form_is_comprehensive):
    """
    Saves an existing item data

    *conf* is the root configuration object that the modified object has been extracted from
    *data* is the object that should be modified, extracted from *config*
    *form* is the form instance containing the changes that should be applied to *data*
    *form_is_comprehensive* determines if the form contains ALL of the possible directives of the target data object.
      If True, any directive in the original data that is not in the form will be removed. If false, only directives
      present in the form with an empty value will be removed.
    """
    # Extract filled fields from the form
    fdata = {k.name:k.data for k in form}
    did_change = False

    # Turn arrays into strings ['a','b','c'] => 'a,b,c'
    for k, v in fdata.iteritems():
        if isinstance(v, list):
            fdata[k] = ','.join(v)

    attr = data['meta']['defined_attributes']
    for i in attr:
        if i not in fdata:
            # If the form is NOT comprehensive, do not remove a key that is not in the form
            if form_is_comprehensive:
                # Remove
                print 'Remove ' + i
                data[i] = None
                did_change = True
        elif not fdata[i]:
            print 'Remove ' + i
            data[i] = None
            did_change = True

        elif str(fdata[i].encode('utf-8')) != attr[i]:
            # Edit
            currentval = fdata[i].encode('utf-8')
            print 'Changing {0} from {1} to {2}'.format(i, attr[i], currentval)
            data[i] = currentval
            did_change = True

    for k, v in fdata.iteritems():
        if v is not None and v != '' and v != [] and k not in attr:
            # Create
            print 'Creating attribute {0}={1}'.format(k, v)
            data[k] = v
            # If we don't remove the field name from the data's template fields, it won't be saved by pynag
            if k in data['meta']['template_fields']:
                del data['meta']['template_fields'][k]
            did_change = True

    if did_change:
        print 'Commiting !! ' + data['meta']['filename']
        data['meta']['needs_commit'] = True
        conf.commit()
    return did_change


# #########################################################################################################
# Form tools

def _fillform(form, data):
    form.loaderrors = []
    typedata = getattr(shinken.objects, data['meta']['object_type'].title(), None)
    for k,v in data['meta']['defined_attributes'].iteritems():
        field = getattr(form, k, None)
        if field is not None:
            # Check if the data is a boolean
            if typedata and k in typedata.properties and isinstance(typedata.properties[k], BoolProp):
                # It is; normalize all different boolean syntaxes so it's only '0' or '1'
                try:
                    v = 'on' if BoolProp.pythonize(v) else 'off'
                except PythonizeError:
                    form.loaderrors.append('{0} ({1})'.format(field.label.text, k))
                    field.loaderror = 'This field contained an invalid boolean value ({0}), and has been cleared.'.format(v)
                    continue
            if isinstance(field, SelectMultipleField):
                # Split the names list into an array
                check = [i.strip() for i in v.split(',')]
                v = []
                for name, val in field.choices:
                    if name in check:
                        v.append(name)
                # Did we find everything ?
                if len(v) < len(check):
                    # No, some values missing.
                    form.loaderrors.append('{0} ({1})'.format(field.label.text, k))
                    field.loaderror = 'This field contained unkown elements ({0}), which have been removed.'.format(', '.join([i for i in check if i not in v]))
                field.process(None, v)
            elif isinstance(field, SelectField):
                # Check that the current value is available
                # If not we'll consider it to be a configuration error
                for name, val in field.choices:
                    if name == v:
                        break
                else:
                    # Current value not available
                    form.loaderrors.append('{0} ({1})'.format(field.label.text, k))
                    field.loaderror = 'This field contained an element that does not exist ({0}), and it has been cleared.'.format(v)
            else:
                field.process(None, v.decode('latin1'))
    return len(form.loaderrors) == 0

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
    if value is None or value == ['']:
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
    # A template ?
    is_template = False
    if type.endswith('template'):
        is_template = True
        type = type[:-8]
    if key is None:
        if is_template:
            key = 'name'
        else:
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
    return [('', '<unspecified>'), ('on', 'Yes'), ('off', 'No')]

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
    labels = TextField('Labels')

    #Structure
    parents = SelectMultipleField('Parents', choices=_listobjects_choices('host'))
    hostgroups = SelectMultipleField('Host groups', choices=_listobjects_choices('hostgroup'))
    realm = SelectField('Realm', choices=_listobjects_choices('realm', True))
    service_overrides = TextField('Service overrides')
    service_excludes = SelectMultipleField('Poller tag', choices=_listobjects_choices('service', False, 'service_description'))
    name = TextField('Template name')
    use = SelectMultipleField('Template used', choices=_listobjects_choices('hosttemplate'))
    register = SelectField('Register', choices=_listboolean_choices())

    #Checking
    check_command = SelectField('Check command', choices=_listobjects_choices('command', True))
    initial_state = SelectField('Initial state', choices=[('', '<unspecified>'), ('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])
    max_check_attempts = IntegerField('Maximum check attempts', validators=[validators.Optional(), validators.NumberRange(0)])
    check_interval = IntegerField('Check interval', validators=[validators.Optional(), validators.NumberRange(0)])
    retry_interval = IntegerField('Retry interval', validators=[validators.Optional(), validators.NumberRange(0)])
    active_checks_enabled = SelectField('Enable active notifications', choices=_listboolean_choices())
    passive_checks_enabled = SelectField('Enable passive notifications', choices=_listboolean_choices())
    check_period = SelectField('Check period', choices=_listobjects_choices('timeperiod', True))
    maintenance_period = SelectField('Maintenance period', choices=_listobjects_choices('timeperiod', True))
    obsess_over_host = SelectField('Obsess over host', choices=_listboolean_choices())
    check_freshness = SelectField('Check freshness', choices=_listboolean_choices())
    freshness_threshold = IntegerField('Freshness threshold', validators=[validators.Optional(), validators.NumberRange(0)])
    poller_tag = TextField('Poller tag') # TODO : Show a list of existing tags + 'None' ?
    resultmodulations = SelectMultipleField('Result modulations', choices=_listobjects_choices('resultmodulation'))

    #Status management
    event_handler = SelectField('Event handler', choices=_listobjects_choices('command', True))
    event_handler_enabled = SelectField('Event handler enabled', choices=_listboolean_choices())
    low_flap_threshold = IntegerField('Low flap threshold', validators=[validators.Optional(), validators.NumberRange(0)])
    high_flap_threshold = IntegerField('High flap threshold', validators=[validators.Optional(), validators.NumberRange(0)])
    flap_detection_enabled = SelectField('Flap detection enabled', choices=_listboolean_choices())
    flap_detection_options = SelectMultipleField('Flap detection options', choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])
    retain_status_information = SelectField('Retain status info', choices=_listboolean_choices())
    retain_nonstatus_information = SelectField('Retain non-status info', choices=_listboolean_choices())

    #Notifications
    notifications_enabled = SelectField('Enable notifications', choices=_listboolean_choices())
    contacts = SelectMultipleField('Contacts', choices=_listobjects_choices('contact'))
    contact_groups = SelectMultipleField('Contact groups', choices=_listobjects_choices('contactgroup'))
    notification_interval = IntegerField('Notification interval', validators=[validators.Optional(), validators.NumberRange(0)])
    first_notification_delay = IntegerField('First notification delay', validators=[validators.Optional(), validators.NumberRange(0)])
    notification_period = SelectField('Notification period', choices=_listobjects_choices('timeperiod', True))
    notification_options = SelectMultipleField('Notification options', choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])
    escalations = SelectMultipleField('Escalations', choices=_listobjects_choices('escalation'))

    # Business rules
    business_impact = IntegerField('Business impact', validators=[validators.Optional(), validators.NumberRange(0, 5)])
    business_impact_modulations = SelectMultipleField('Business impact modulations', choices=_listobjects_choices('businessimpactmodulation'))
    business_rule_output_template = TextField('Business rule output template')
    business_rule_smart_notifications = SelectField('Enable smart notifications', choices=_listboolean_choices())
    business_rule_downtime_as_ack = SelectField('Include downtimes in smart notifications', choices=_listboolean_choices())
    business_rule_host_notification_options = SelectMultipleField('Business rule host notification options', choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])
    business_rule_service_notification_options = SelectMultipleField('Business rule service notification options', choices=[('w','Warning (w)'), ('u','Unknown (u)'), ('c', 'Critical (c)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])

    #Snapshots
    snapshot_enabled = SelectField('Enable snapshot', choices=_listboolean_choices())
    snapshot_command = SelectField('Snapshot command', choices=_listobjects_choices('command', True))
    snapshot_period = SelectField('Snapshot period', choices=_listobjects_choices('timeperiod', True))
    snapshot_criteria = SelectMultipleField('Snapshot criteria', choices=[('d','Down (d)'), ('u','Unknown (u)')])
    snapshot_interval = IntegerField('Snapshot interval', validators=[validators.Optional(), validators.NumberRange(0)])

    # Misc.
    process_perf_data = SelectField('Process perf data', choices=_listboolean_choices())
    stalking_options = SelectMultipleField('Stalking options', choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])
    trigger_broker_raise_enabled = SelectField('Enable trigger', choices=_listboolean_choices())
    trigger_name = TextField('Trigger name')

class HostGroupForm(Form):
    # Description
    hostgroup_name = TextField('Hostgroup name')
    alias = TextField('Alias')
    notes = TextAreaField('Notes')
    notes_url = URLField('Notes URL')
    action_url = URLField('Action URL')

    #Structure
    members = SelectMultipleField('Members', choices=_listobjects_choices('host'))
    hostgroup_members = SelectMultipleField('Host groups', choices=_listobjects_choices('hostgroup'))
    realm = SelectField('Realm', choices=_listobjects_choices('realm', True))
    name = TextField('Template name')
    use = SelectMultipleField('Template used', choices=_listobjects_choices('hostgrouptemplate'))
    register = SelectField('Register', choices=_listboolean_choices())

class ServiceForm(Form):
    #Description
    service_description = TextField('Service description')
    display_name = TextField('Display name')
    notes = TextAreaField('Notes')
    notes_url = URLField('Notes URL')
    action_url = URLField('Action URL')
    labels = TextField('Labels')

    # Structure
    host_name = SelectMultipleField('Host', choices=_listobjects_choices('host'))
    # We cannot use the classic SelectMUltipleField for this field, because of the expression syntax available on this field that may get in the way
    hostgroup_name = TextField('Host group')
    host_dependency_enabled = SelectField('Host dependency enabled', choices=_listboolean_choices())
    servicegroups = SelectMultipleField('Service groups', choices=_listobjects_choices('servicegroup'))
    service_dependencies = SelectMultipleField('Service dependencies', choices=_listobjects_choices('service'))
    name = TextField('Template name')
    use = SelectMultipleField('Template used', choices=_listobjects_choices('servicetemplate'))
    register = SelectField('Register', choices=_listboolean_choices())

    # Checking
    check_command = SelectField('Check command', choices=_listobjects_choices('command', True))
    initial_state = SelectField('Initial state', choices=[('o','Ok (o)'), ('w','Warning (w)'), ('u','Unknown (u)'), ('c','Critical (c)')])
    max_check_attempts = IntegerField('Max check attempts', validators=[validators.Optional(), validators.NumberRange(0)])
    check_interval = IntegerField('Check interval', validators=[validators.Optional(), validators.NumberRange(0)])
    retry_interval = IntegerField('Retry interval', validators=[validators.Optional(), validators.NumberRange(0)])
    active_checks_enabled = SelectField('Enable active checks', choices=_listboolean_choices())
    passive_checks_enabled = SelectField('Enable passive checks', choices=_listboolean_choices())
    check_period = SelectField('Check period', choices=_listobjects_choices('timeperiod', True))
    maintenance_period = SelectField('Maintenance period', choices=_listobjects_choices('timeperiod', True))
    is_volatile = SelectField('Is volatile', choices=_listboolean_choices())
    obsess_over_service = SelectField('Obsess over service', choices=_listboolean_choices())
    check_freshness = SelectField('Check freshness', choices=_listboolean_choices())
    freshness_threshold = IntegerField('Freshness threshold', validators=[validators.Optional(), validators.NumberRange(0)])
    poller_tag = TextField('Poller tag') # TODO : Show a list of existing tags + 'None' ?

    # Status management
    event_handler = SelectField('Event handler', choices=_listobjects_choices('command', True))
    event_handler_enabled = SelectField('Event handler enabled', choices=_listboolean_choices())
    flap_detection_enabled = SelectField('Flap detection enabled', choices=_listboolean_choices())
    low_flap_threshold = IntegerField('Low flap threshold', validators=[validators.Optional(), validators.NumberRange(0)])
    high_flap_threshold = IntegerField('High flap threshold', validators=[validators.Optional(), validators.NumberRange(0)])
    flap_detection_options = SelectMultipleField('Flap detection options', choices=[('o','Ok (o)'), ('w','Warning (w)'), ('c', 'Critical (c)'), ('u','Unknown (u)')])
    retain_status_information = SelectField('Retain status info', choices=_listboolean_choices())
    retain_nonstatus_information = SelectField('Retain non-status info', choices=_listboolean_choices())

    # Notifications
    notifications_enabled = SelectField('Enable notifications', choices=_listboolean_choices())
    contacts = SelectMultipleField('Contacts', choices=_listobjects_choices('contact'))
    contact_groups = SelectMultipleField('Contact groups', choices=_listobjects_choices('contactgroup'))
    notification_interval = IntegerField('Notification interval', validators=[validators.Optional(), validators.NumberRange(0)])
    first_notification_delay = IntegerField('First notification delay', validators=[validators.Optional(), validators.NumberRange(0)])
    notification_period = SelectField('Notification period', choices=_listobjects_choices('timeperiod', True))
    notification_options = SelectMultipleField('Notification options', choices=[('w','Warning (d)'), ('u','Unknown (u)'), ('c', 'Critical (c)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])

    # Business rules
    business_impact = IntegerField('Business impact', validators=[validators.Optional(), validators.NumberRange(0, 5)])
    business_rule_output_template = TextField('Business rule output template')
    business_rule_smart_notifications = SelectField('Enable smart notifications', choices=_listboolean_choices())
    business_rule_downtime_as_ack = SelectField('Include downtimes in smart notifications', choices=_listboolean_choices())
    business_rule_host_notification_options = SelectMultipleField('Business rule host notification options', choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])
    business_rule_service_notification_options = SelectMultipleField('Business rule service notification options', choices=[('w','Warning (w)'), ('u','Unknown (u)'), ('c', 'Critical (c)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')])

    # Snapshot
    snapshot_enabled = SelectField('Enable snapshot', choices=_listboolean_choices())
    snapshot_command = SelectField('Snapshot command', choices=_listobjects_choices('command', True))
    snapshot_period = SelectField('Snapshot period', choices=_listobjects_choices('timeperiod', True))
    snapshot_criteria = SelectMultipleField('Snapshot criteria', choices=[('d','Down (d)'), ('u','Unknown (u)')])
    snapshot_interval = IntegerField('Snapshot interval', validators=[validators.Optional(), validators.NumberRange(0)])

    # Misc.
    process_perf_data = SelectField('Process perf data', choices=_listboolean_choices())
    stalking_options = SelectMultipleField('Stalking options', choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')])
    duplicate_foreach = TextField('Duplicate for each')
    trigger_broker_raise_enabled = SelectField('Enable trigger', choices=_listboolean_choices())
    trigger_name = TextField('Trigger name')

class ServiceGroupForm(Form):
    #Description
    servicegroup_name = TextField('ServiceGroup name')
    alias = TextField('alias')
    members = SelectMultipleField('Services', choices=_listobjects_choices('services', True))
    servicegroup_members = SelectMultipleField('Services', choices=_listobjects_choices('servicegroup', True))
    notes = TextField('Note string')
    notes_url = URLField('Notes URL')
    action_url = URLField('Action URL')
    
class ContactForm(Form):
    #Description
    contact_name = TextField('Host name')
    alias = TextField(u'Alias')
    contactgroups = TextField('Contact group')
    host_notification_enabled = SelectField('host_notification_enabled',choices=_listboolean_choices())
    service_notification_enabled = SelectField('service_notification_enabled',choices=_listboolean_choices())
    host_notification_period = SelectField('Host notification period', choices=_listobjects_choices('timeperiod', True))
    service_notification_period = SelectField('Service notification period', choices=_listobjects_choices('timeperiod', True))
    host_notification_options = SelectMultipleField('Service notification options', choices=[('d','d'),('u','u'),('r','r'),('f','f'),('s','s'),('n','n')])
    service_notification_options = SelectMultipleField('Service notification options', choices=[('w','w'),('u','u'),('c','c'),('r','r'),('f','f'),('s','s'),('n','n')])
    host_notification_commands = TextField('Host notification command')
    server_notification_commands = TextField('Service notification command')
    email = TextField('Email')
    pager = TextField('Pager')
    addressx = TextField('additional_contact_address')
    can_submit_commands = SelectField('can_submit_commands',choices=_listboolean_choices())
    retain_status_information = SelectField('retain_status_information',choices=_listboolean_choices())
    retain_nonstatus_information = SelectField('retain_nonstatus_information',choices=_listboolean_choices())

class ContactGroupForm(Form):
    #Description
    contactgroup_name = TextField('Host name')
    alias = TextField(u'Alias')
    #Members
    members = SelectMultipleField('Members', choices=_listobjects_choices('contact', True))
    contactgroup_members = SelectMultipleField('Contact groups members', choices=_listobjects_choices('contactgroup', True))
 
