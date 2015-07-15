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
import pynag.Model

from flask import jsonify, render_template, abort, request, redirect
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

import re

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
    #if no objid given we are creating a new configuration file
    if objid is None:
        setattr(formtype,'filename',TextField('Configuration file name'))
        form = formtype(request.form)
        #_annotateform(form, target)
        if request.method == 'POST':
            print 'iz POST!'
            if form.validate():
                # Save !
                _save_new(form, objtype)
                #TODO: redirect to list
                return redirect('/config#'+objtype)
            else:
                print 'iz not valid :('
                #_fillform(form,)
                return render_template('config/details-{0}.html'.format(objtype), type=objtype, form=form, data={})

        else: #GET
            return render_template('config/details-{0}.html'.format(objtype), type=objtype, form=form, data={})

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


    _addtimeperiodsfield(formtype, target)
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


#lists & delete
@app.route('/config')
@login_required
def config_list():
    return render_template('config/list.html')

@app.route('/config/delete/<typeid>/<objid>',methods=['GET','POST'])
def delete_conf(typeid,objid):
    conf = _getconf()
    #TODO: handle templates
    primkey = _typekeys[typeid]
    targettype = getattr(pynag.Model,typeid.capitalize())
    args = {}
    args[primkey] = objid
    for target in targettype.objects.filter(**args):
        target.delete()
    return redirect('/config#'+typeid)

#hosts
@app.route('/config/host/create', methods=['GET', 'POST'])
@login_required
def host_create():
    return _get_details('host', False, None, HostForm)

@app.route('/config/host/<objid>', methods=['GET', 'POST'])
@login_required
def host_details(objid):
    return _get_details('host', False, objid, HostForm)

@app.route('/config/hosttemplate/<objid>', methods=['GET', 'POST'])
@login_required
def hosttemplate_details(objid):
    return _get_details('host', True, objid, HostForm)

#hostgroup
@app.route('/config/hostgroup/create', methods=['GET', 'POST'])
@login_required
def hostgroup_create():
    return _get_details('hostgroup', False, None, HostGroupForm)

@app.route('/config/hostgroup/<objid>', methods=['GET', 'POST'])
@login_required
def hostgroup_details(objid):
    return _get_details('hostgroup', False, objid, HostGroupForm)

@app.route('/config/hostgrouptemplate/<objid>', methods=['GET', 'POST'])
@login_required
def hostgrouptemplate_details(objid):
    return _get_details('hostgroup', True, objid, HostGroupForm)

#services
@app.route('/config/service/create', methods=['GET', 'POST'])
@login_required
def service_create():
    return _get_details('service', False, None, ServiceForm)

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

#services group
@app.route('/config/servicegroup/create', methods=['GET', 'POST'])
@login_required
def servicegroup_create():
    return _get_details('servicegroup', False, None, ServiceGroupForm)

@app.route('/config/servicegroup/<objectid>', methods=['GET', 'POST'])
@login_required
def servicegroup_details(objectid):
    return _get_details('servicegroup', False, objectid, ServiceGroupForm)

@app.route('/config/servicegrouptemplate/<objid>', methods=['GET', 'POST'])
@login_required
def servicegrouptemplate_details(objid):
    return _get_details('servicegroup', True, objid, ServiceGroupForm)


#contacts
@app.route('/config/contact/create', methods=['GET', 'POST'])
@login_required
def contact_create():
    return _get_details('contact', False, None, ContactForm)

@app.route('/config/contact/<contactid>', methods=['GET', 'POST'])
@login_required
def contact_details(contactid):
    return _get_details('contact', False, contactid, ContactForm)

@app.route('/config/contacttemplate/<objid>', methods=['GET', 'POST'])
@login_required
def contacttemplate_details(objid):
    return _get_details('contact', True, objid, ContactForm)

#contacts group
@app.route('/config/contactgroup/create', methods=['GET', 'POST'])
@login_required
def contactgroup_create():
    return _get_details('contactgroup', False, None, ContactGroupForm)

@app.route('/config/contactgroup/<objectid>', methods=['GET', 'POST'])
@login_required
def contactgroup_details(objectid):
    return _get_details('contactgroup', False, objectid, ContactGroupForm)

@app.route('/config/contactgrouptemplate/<objid>', methods=['GET', 'POST'])
@login_required
def contactgrouptemplate_details(objid):
    return _get_details('contactgroup', True, objid, ContactGroupForm)

#time periods
@app.route('/config/timeperiod/create', methods=['GET', 'POST'])
@login_required
def timeperiod_create():
    return _get_details('timeperiod', False, None, TimeperiodForm)

@app.route('/config/timeperiod/<objectid>', methods=['GET', 'POST'])
@login_required
def timeperiod_details(objectid):
    return _get_details('timeperiod', False, objectid, TimeperiodForm)

@app.route('/config/timeperiodtemplate/<objid>', methods=['GET', 'POST'])
@login_required
def timeperiodtemplate_details(objid):
    return _get_details('timeperiod', True, objid, TimeperiodForm)

#commands
@app.route('/config/command/create', methods=['GET', 'POST'])
@login_required
def command_create():
    return _get_details('command', False, None, CommandForm)

@app.route('/config/command/<objectid>', methods=['GET', 'POST'])
@login_required
def command_details(objectid):
    return _get_details('command', False, objectid, CommandForm)

@app.route('/config/commandtemplate/<objid>', methods=['GET', 'POST'])
@login_required
def commandtemplate_details(objid):
    return _get_details('command', True, objid, CommandForm)


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


def _save_new(form,targettype):
    """ """
    # Extract filled fields from the form
    fdata = {k.name:k.data for k in form}
    filename = fdata['filename'];

    targettype = targettype.capitalize()
    conftype = getattr(pynag.Model,targettype)
    new_conf = conftype()

    # Turn arrays into strings ['a','b','c'] => 'a,b,c'
    for k, v in fdata.iteritems():
        if k == 'filename':
            next
        if isinstance(v, list):
            v = [v for v in v if v]
            fdata[k] = ','.join(v)

        setattr(new_conf,k,v)

    app.logger.error('Commiting !! ' + filename)
    new_conf.set_filename(filename)
    new_conf.save()
    return True

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
            #trololololo, more seriously, this is to prevent empty values in list
            v = [v for v in v if v]
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

        elif fdata[i].encode('utf8') != attr[i]:
            # Edit
            currentval = fdata[i]
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

        #apply descriptions as comments
        for d in data['meta']['descriptions']:
            if data[d]:
                data[d] = data[d] + "\t; " + data['meta']['descriptions'][d]

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
                    v = 1 if BoolProp.pythonize(v) else 0
                    field.process(None, v)
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
                    if str(val) == str(v):
                        break
                else:
                    # Current value not available
                    form.loaderrors.append('{0} ({1})'.format(field.label.text, k))
                    field.loaderror = 'This field contained an element that does not exist ({0}), and it has been cleared.'.format(v)
                field.process(None, v)
            else:
                field.process(None, unicode(v,'utf-8',errors='replace'))
    return len(form.loaderrors) == 0

#Add timeperiod exception fields to form and meta data
def _addtimeperiodsfield(form,data):
    ''' Add custom field (unsuported by pynag) '''
    data['meta']['custom'] = []
    data['meta']['descriptions'] = {}
    reg = re.compile('(.+)\s+([\d\-:]+)\s*\;?(.*)')
    tmp = {}
    removeme = []
    for d in data:
        if d and not data[d]:
            m = reg.match(d)
            if(m):
                r = m.groups()
                field = r[0].strip()
                dates = r[1]
                meta = r[2]
                data['meta']['defined_attributes'][field] = dates
                removeme.append(d);
                if field not in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']:
                    setattr(form,field, TextField(field, description= meta))
                    data['meta']['custom'].append(field)
                    data['meta']['descriptions'][field] = meta
                    tmp[field] = dates
    for d in tmp:
        data[d] = tmp[d]
    for d in removeme:
        del data[d]
        del data['meta']['defined_attributes'][d]

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
    return [('', '<unspecified>'), (1, 'Yes'), (0, 'No')]

# #########################################################################################################
# Forms

class HostForm(Form):
    #Description
    host_name = TextField(
        'Host name',
        description='This directive is used to define a short name used to identify the host. It is used in host group and service definitions to reference this particular host. Hosts can have multiple services (which are monitored) associated with them.'
    )
    alias = TextField(
        'Alias',
        description='This directive is used to define a longer name or description used to identify the host. It is provided in order to allow you to more easily identify a particular host.'
    )
    display_name = TextField(
        'Display name',
        description='This directive is used to define an alternate name that should be displayed in the web interface for this host. If not specified, this defaults to the value you specify for the host_name directive.'
    )
    address = TextField(
        'Address',
        description='This directive is used to define the address of the host. Normally, this is an IP address, although it could really be anything you want (so long as it can be used to check the status of the host). You can use a FQDN to identify the host instead of an IP address, but if "DNS" services are not available this could cause problems.'
    )
    notes = TextAreaField(
        'Notes',
        description='This directive is used to define an optional string of notes pertaining to the host.'
    )
    notes_url = URLField(
        'Notes URL',
        description='This variable is used to define an optional URL that can be used to provide more information about the host.'
    )
    action_url = URLField(
        'Action URL',
        description='This directive is used to define one or more optional URL that can be used to provide more actions to be performed on the host.'
    )
    labels = TextField(
        'Labels',
        description='This variable may be used to place arbitrary labels (separated by comma character). Those labels may be used in other configuration objects such as business rules grouping expressions.'
    )

    #Structure
    parents = SelectMultipleField(
        'Parents',
        choices=_listobjects_choices('host'),
        description='This directive is used to define a list of short names of "parent" hosts for this particular host. Parent hosts are typically routers, switches, firewalls, etc. that lie between the monitoring host and a remote hosts.'
    )
    hostgroups = SelectMultipleField(
        'Host groups',
        choices=_listobjects_choices('hostgroup'),
        description='This directive is used to identify the short name(s) of the hostgroup(s) that the host belongs to.'
    )
    realm = SelectField(
        'Realm',
        choices=_listobjects_choices('realm', True),
        description='This variable is used to define the realm where the host will be put. By putting the host in a realm, it will be manage by one of the scheduler of this realm.'
    )
    service_overrides = TextField(
        'Service overrides',
        description='This variable may be used to override services directives for a specific host. This is especially useful when services are inherited (for instance from packs), because it allows to have a host attached service set one of its directives a specific value.'
    )
    service_excludes = SelectMultipleField(
        'Poller tag',
        choices=_listobjects_choices('service', False, 'service_description'),
        description='This variable may be used to exclude a service from a host. It addresses the situations where a set of serices is inherited from a pack or attached from a hostgroup, and an identified host should NOT have one (or more, comma separated) services defined.'
    )
    name = TextField(
        'Template name'
    )
    use = SelectMultipleField(
        'Template used',
        choices=_listobjects_choices('hosttemplate')
    )
    register = SelectField(
        'Register',
        choices=_listboolean_choices()
    )

    #Checking
    check_command = SelectField(
        'Check command',
        choices=_listobjects_choices('command', True),
        description='This directive is used to specify the short name of the command that should be used to check if the host is up or down. Typically, this command would try and ping the host to see if it is "alive". The command must return a status of OK (0) or Shinken will assume the host is down. If you leave this argument blank, the host will not be actively checked. Thus, Shinken will likely always assume the host is up (it may show up as being in a "PENDING" state in the web interface). This is useful if you are monitoring printers or other devices that are frequently turned off. The maximum amount of time that the notification command can run is controlled by the host_check_timeout option.'
    )
    initial_state = SelectField(
        'Initial state',
        choices=[('', '<unspecified>'), ('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')],
        description='By default Shinken will assume that all hosts are in UP states when in starts.'
    )
    max_check_attempts = IntegerField(
        'Maximum check attempts',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of times that Shinken will retry the host check command if it returns any state other than an OK state. Setting this value to 1 will cause Shinken to generate an alert without retrying the host check again.'
    )
    check_interval = IntegerField(
        'Check interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" between regularly scheduled checks of the host. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. More information on this value can be found in the check scheduling documentation.'
    )
    retry_interval = IntegerField(
        'Retry interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" to wait before scheduling a re-check of the hosts. Hosts are rescheduled at the retry interval when they have changed to a non-UP state. Once the host has been retried max_check_attempts times without a change in its status, it will revert to being scheduled at its "normal" rate as defined by the check_interval value. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes.'
    )
    active_checks_enabled = SelectField(
        'Enable active notifications',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not active checks (either regularly scheduled or on-demand) of this host are enabled.'
    )
    passive_checks_enabled = SelectField(
        'Enable passive notifications',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not passive checks are enabled for this host.'
    )
    check_period = SelectField(
        'Check period',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short name of the time period during which active checks of this host can be made.'
    )
    maintenance_period = SelectField(
        'Maintenance period',
        choices=_listobjects_choices('timeperiod', True),
        description='Shinken-specific variable to specify a recurring downtime period. This works like a scheduled downtime, so unlike a check_period with exclusions, checks will still be made (no "blackout" times).'
    )
    obsess_over_host = SelectField(
        'Obsess over host',
        choices=_listboolean_choices(),
        description='This directive determines whether or not checks for the host will be "obsessed" over using the ochp_command.'
    )
    check_freshness = SelectField(
        'Check freshness',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not freshness checks are enabled for this host.'
    )
    freshness_threshold = IntegerField('Freshness threshold', validators=[validators.Optional(), validators.NumberRange(0)],description='This directive is used to specify the freshness threshold (in seconds) for this host. If you set this directive to a value of 0, Shinken will determine a freshness threshold to use automatically.')
    poller_tag = TextField(
        'Poller tag',
        description='This variable is used to define the poller_tag of the host. All checks of this hosts will only take by pollers that have this value in their poller_tags parameter.By default the pollerag value is \'None\', so all untagged pollers can take it because None is set by default for them.'
    ) # TODO : Show a list of existing tags + 'None' ?
    resultmodulations = SelectMultipleField(
        'Result modulations',
        choices=_listobjects_choices('resultmodulation'),
        description='This variable is used to link with resultmodulations objects. It will allow such modulation to apply, like change a warning in critical for this host.'
    )

    #Status management
    event_handler = SelectField(
        'Event handler',
        choices=_listobjects_choices('command', True),
        description='This directive is used to specify the short name of the command that should be run whenever a change in the state of the host is detected (i.e. whenever it goes down or recovers). Read the documentation on event handlers for a more detailed explanation of how to write scripts for handling events. The maximum amount of time that the event handler command can run is controlled by the event_handler_timeout option.'
    )
    event_handler_enabled = SelectField(
        'Event handler enabled',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the event handler for this host is enabled.'
    )
    low_flap_threshold = IntegerField(
        'Low flap threshold',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to specify the low state change threshold used in flap detection for this host. More information on flap detection can be found here. If you set this directive to a value of 0, the program-wide value specified by the low_host_flap_threshold directive will be used.'
    )
    high_flap_threshold = IntegerField(
        'High flap threshold',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to specify the high state change threshold used in flap detection for this host. More information on flap detection can be found here. If you set this directive to a value of 0, the program-wide value specified by the high_host_flap_threshold directive will be used.'
    )
    flap_detection_enabled = SelectField(
        'Flap detection enabled',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not flap detection is enabled for this host. More information on flap detection can be found here.'
    )
    flap_detection_options = SelectMultipleField(
        'Flap detection options',
        choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')],
        description='This directive is used to determine what host states the flap detection logic will use for this host.'
    )
    retain_status_information = SelectField(
        'Retain status info',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not status-related information about the host is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive. '
    )
    retain_nonstatus_information = SelectField(
        'Retain non-status info',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not non-status information about the host is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive. '
    )

    #Notifications
    notifications_enabled = SelectField(
        'Enable notifications',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not notifications for this host are enabled.'
    )
    contacts = SelectMultipleField(
        'Contacts',
        choices=_listobjects_choices('contact'),
        description='This is a list of the short names of the contacts that should be notified whenever there are problems (or recoveries) with this host.'
    )
    contact_groups = SelectMultipleField(
        'Contact groups',
        choices=_listobjects_choices('contactgroup'),
        description='This is a list of the short names of the contact groups that should be notified whenever there are problems (or recoveries) with this host.'
    )
    notification_interval = IntegerField(
        'Notification interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" to wait before re-notifying a contact that this service is still down or unreachable. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, Shinken will not re-notify contacts about problems for this host - only one problem notification will be sent out.'
    )
    first_notification_delay = IntegerField(
        'First notification delay',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" to wait before sending out the first problem notification when this host enters a non-UP state. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, Shinken will start sending out notifications immediately.'
    )
    notification_period = SelectField(
        'Notification period',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short name of the time period during which notifications of events for this host can be sent out to contacts. If a host goes down, becomes unreachable, or recoveries during a time which is not covered by the time period, no notifications will be sent out.'
    )
    notification_options = SelectMultipleField(
        'Notification options',
        choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')],
        description='This directive is used to determine when notifications for the host should be sent out.'
    )
    escalations = SelectMultipleField(
        'Escalations',
        choices=_listobjects_choices('escalation'),
        description='This variable is used to link with escalations objects. It will allow such escalations rules to appy.'
    )

    # Business rules
    business_impact = IntegerField(
        'Business impact',
        validators=[validators.Optional(), validators.NumberRange(0, 5)],
        description='This variable is used to set the importance we gave to this host for the business from the less important (0 = nearly nobody will see if it\'s in error) to the maximum (5 = you lost your job if it fail).'
    )
    business_impact_modulations = SelectMultipleField(
        'Business impact modulations',
        choices=_listobjects_choices('businessimpactmodulation'),
        description='This variable is used to link with business_impact_modulations objects. It will allow such modulation to apply (for example if the host is a payd server, it will be important only in a specific timeperiod: near the payd day).'
    )
    business_rule_output_template = TextField(
        'Business rule output template',
        description='Classic host check output is managed by the underlying plugin (the check output is the plugin stdout).'
    )
    business_rule_smart_notifications = SelectField(
        'Enable smart notifications',
        choices=_listboolean_choices(),
        description='This variable may be used to activate smart notifications on business rules. This allows to stop sending notification if all underlying problems have been acknowledged.'
    )
    business_rule_downtime_as_ack = SelectField(
        'Include downtimes in smart notifications',
        choices=_listboolean_choices()
    )
    business_rule_host_notification_options = SelectMultipleField(
        'Business rule host notification options',
        choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')],
        description='This option allows to enforce business rules underlying hosts notification options to easily compose a consolidated meta check. This is especially useful for business rules relying on grouping expansion.'
    )
    business_rule_service_notification_options = SelectMultipleField(
        'Business rule service notification options',
        choices=[('w','Warning (w)'), ('u','Unknown (u)'), ('c', 'Critical (c)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')],
        description='This option allows to enforce business rules underlying services notification options to easily compose a consolidated meta check. This is especially useful for business rules relying on grouping expansion.'
    )

    #Snapshots
    snapshot_enabled = SelectField(
        'Enable snapshot',
        choices=_listboolean_choices(),
        description='This option allows to enable snapshots snapshots on this element.'
    )
    snapshot_command = SelectField(
        'Snapshot command',
        choices=_listobjects_choices('command', True),
        description='Command to launch when a snapshot launch occurs'
    )
    snapshot_period = SelectField(
        'Snapshot period',
        choices=_listobjects_choices('timeperiod', True),
        description='Timeperiod when the snapshot call is allowed'
    )
    snapshot_criteria = SelectMultipleField(
        'Snapshot criteria',
        choices=[('d','Down (d)'), ('u','Unknown (u)')],
        description='List of states that enable the snapshot launch. Mainly bad states.'
    )
    snapshot_interval = IntegerField(
        'Snapshot interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='Minimum interval between two launch of snapshots to not hammering the host, in interval_length units (by default 60s).'
    )

    # Misc.
    process_perf_data = SelectField(
        'Process perf data',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the processing of performance data is enabled for this host. '
    )
    stalking_options = SelectMultipleField(
        'Stalking options',
        choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')],
        description='This directive determines which host states "stalking" is enabled for.'
    )
    trigger_broker_raise_enabled = SelectField(
        'Enable trigger',
        choices=_listboolean_choices(),
        description='This option define the behavior of the defined trigger (Default 0). If set to 1, this means the trigger will modify the output / return code of the check.'
    )
    trigger_name = TextField(
        'Trigger name',
        description='This options define the trigger that will be executed after a check result (passive or active). This file trigger_name.trig has to exist in the trigger directory or sub-directories.'
    )

class HostGroupForm(Form):
    # Description
    hostgroup_name = TextField(
        'Hostgroup name',
        description='This directive is used to define a short name used to identify the host group.'
    )
    alias = TextField(
        'Alias',
        description='This directive is used to define is a longer name or description used to identify the host group. It is provided in order to allow you to more easily identify a particular host group.'
    )
    notes = TextAreaField(
        'Notes',
        description='This directive is used to define an optional string of notes pertaining to the host.'
    )
    notes_url = URLField(
        'Notes URL',
        description='This variable is used to define an optional URL that can be used to provide more information about the host group.'
    )
    action_url = URLField(
        'Action URL',
        description='This directive is used to define an optional URL that can be used to provide more actions to be performed on the host group.'
    )

    #Structure
    members = SelectMultipleField(
        'Members',
        choices=_listobjects_choices('host'),
        description='This is a list of the short names of hosts that should be included in this group.This directive may be used as an alternative to (or in addition to) the hostgroups directive in host definitions.'
    )
    hostgroup_members = SelectMultipleField(
        'Host groups',
        choices=_listobjects_choices('hostgroup'),
        description='This optional directive can be used to include hosts from other "sub" host groups in this host group.'
    )
    realm = SelectField(
        'Realm',
        choices=_listobjects_choices('realm', True),
        description='This directive is used to define in which realm all hosts of this hostgroup will be put into. If the host are already tagged by a realm (and not the same), the value taken into account will the the one of the host (and a warning will be raised). If no realm is defined, the default one will be take.'
    )
    name = TextField(
        'Template name'
    )
    use = SelectMultipleField(
        'Template used',
        choices=_listobjects_choices('hostgrouptemplate')
    )
    register = SelectField(
        'Register',
        choices=_listboolean_choices(),description=''
    )

class ServiceForm(Form):
    #Description
    service_description = TextField(
        'Service description',
        description='This directive is used to define the description of the service, which may contain spaces, dashes, and colons (semicolons, apostrophes, and quotation marks should be avoided). No two services associated with the same host can have the same description. Services are uniquely identified with their host_name and service_description directives.'
    )
    display_name = TextField(
        'Display name',
        description='This directive is used to define an alternate name that should be displayed in the web interface for this service. If not specified, this defaults to the value you specify for the service_description directive.'
    )
    notes = TextAreaField(
        'Notes',
        description='This directive is used to define an optional string of notes pertaining to the service.'
    )
    notes_url = URLField(
        'Notes URL',
        description='This directive is used to define an optional URL that can be used to provide more information about the service. '
    )
    action_url = URLField(
        'Action URL',
        description='This directive is used to define an optional URL that can be used to provide more actions to be performed on the service. '
    )
    labels = TextField(
        'Labels',
        description='This variable may be used to place arbitrary labels (separated by comma character). Those labels may be used in other configuration objects such as business rules to identify groups of services.'
    )

    # Structure
    host_name = SelectMultipleField(
        'Host',
        choices=_listobjects_choices('host')
    )
    # We cannot use the classic SelectMUltipleField for this field, because of the expression syntax available on this field that may get in the way
    hostgroup_name = TextField(
        'Host group'
    )
    host_dependency_enabled = SelectField(
        'Host dependency enabled',
        choices=_listboolean_choices(),
        description='This variable may be used to remove the dependency between a service and its parent host. Used for volatile services that need notification related to itself and not depend on the host notifications.'
    )
    servicegroups = SelectMultipleField(
        'Service groups',
        choices=_listobjects_choices('servicegroup'),
        description='This directive is used to identify the short name(s) of the servicegroup(s) that the service belongs to. Multiple servicegroups should be separated by commas. This directive may be used as an alternative to using the members directive in servicegroup definitions.'
    )
    service_dependencies = SelectMultipleField(
        'Service dependencies',
        choices=_listobjects_choices('service'),
        description='TODO advanced mode only?'
    )
    name = TextField(
        'Template name'
    )
    use = SelectMultipleField(
        'Template used',
        choices=_listobjects_choices('servicetemplate')
    )
    register = SelectField(
        'Register',
        choices=_listboolean_choices()
    )

    # Checking
    check_command = SelectField(
        'Check command',
        choices=_listobjects_choices('command', True),
        description='This directive is used to specify the short name of the command that Shinken will run in order to check the status of the service. The maximum amount of time that the service check command can run is controlled by the service_check_timeout option. There is also a command with the reserved name "bp_rule". It is defined internally and has a special meaning. Unlike other commands it mustn\'t be registered in a command definition. It\'s purpose is not to execute a plugin but to represent a logical operation on the statuses of other services.'
    )
    initial_state = SelectField(
        'Initial state',
        choices=[('o','Ok (o)'), ('w','Warning (w)'), ('u','Unknown (u)'), ('c','Critical (c)')],
        description='By default Shinken will assume that all services are in OK states when in starts. You can override the initial state for a service by using this directive.'
    )
    max_check_attempts = IntegerField(
        'Max check attempts',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of times that Shinken will retry the service check command if it returns any state other than an OK state. Setting this value to 1 will cause Shinken to generate an alert without retrying the service check again.'
    )
    check_interval = IntegerField(
        'Check interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
    description='This directive is used to define the number of "time units" to wait before scheduling the next "regular" check of the service. "Regular" checks are those that occur when the service is in an OK state or when the service is in a non-OK state, but has already been rechecked max_check_attempts number of times. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. '
    )
    retry_interval = IntegerField(
        'Retry interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" to wait before scheduling a re-check of the service. Services are rescheduled at the retry interval when they have changed to a non-OK state. Once the service has been retried max_check_attempts times without a change in its status, it will revert to being scheduled at its "normal" rate as defined by the check_interval value. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes.'
    )
    active_checks_enabled = SelectField(
        'Enable active checks',
        choices=_listboolean_choices(),
        description='his directive is used to determine whether or not active checks of this service are enabled.'
    )
    passive_checks_enabled = SelectField(
        'Enable passive checks',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not passive checks of this service are enabled. '
    )
    check_period = SelectField(
        'Check period',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short name of the time period during which active checks of this service can be made.'
    )
    maintenance_period = SelectField(
        'Maintenance period',
        choices=_listobjects_choices('timeperiod', True),
        description='Shinken-specific variable to specify a recurring downtime period. This works like a scheduled downtime, so unlike a check_period with exclusions, checks will still be made (no "blackout" times).'
    )
    is_volatile = SelectField(
        'Is volatile',
        choices=_listboolean_choices()
    )
    obsess_over_service = SelectField(
        'Obsess over service',
        choices=_listboolean_choices(),
        description='This directive determines whether or not checks for the service will be "obsessed" over using the ocsp_command.'
    )
    check_freshness = SelectField(
        'Check freshness',
        choices=_listboolean_choices(),description='This directive is used to determine whether or not freshness checks are enabled for this service.'
    )
    freshness_threshold = IntegerField(
        'Freshness threshold',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to specify the freshness threshold (in seconds) for this service. If you set this directive to a value of 0, Shinken will determine a freshness threshold to use automatically.'
    )
    poller_tag = TextField(
        'Poller tag',
        description='This variable is used to define the poller_tag of checks from this service. All of theses checks will be taken by pollers that have this value in their poller_tags parameter. By default there is no poller_tag, so all untaggued pollers can take it.'
    ) # TODO : Show a list of existing tags + 'None' ?

    # Status management
    event_handler = SelectField(
        'Event handler',
        choices=_listobjects_choices('command', True),
        description='This directive is used to specify the short name of the command that should be run whenever a change in the state of the service is detected (i.e. whenever it goes down or recovers).'
    )
    event_handler_enabled = SelectField(
        'Event handler enabled',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the event handler for this service is enabled.'
    )
    flap_detection_enabled = SelectField(
        'Flap detection enabled',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not flap detection is enabled for this service.'
    )
    low_flap_threshold = IntegerField(
        'Low flap threshold',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to specify the low state change threshold used in flap detection for this service. More information on flap detection can be found here. If you set this directive to a value of 0, the program-wide value specified by the low_service_flap_threshold directive will be used.'
    )
    high_flap_threshold = IntegerField(
        'High flap threshold',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to specify the high state change threshold used in flap detection for this service. More information on flap detection can be found here. If you set this directive to a value of 0, the program-wide value specified by the high_service_flap_threshold directive will be used.'
    )
    flap_detection_options = SelectMultipleField(
        'Flap detection options',
        choices=[('o','Ok (o)'), ('w','Warning (w)'), ('c', 'Critical (c)'), ('u','Unknown (u)')],
        description='This directive is used to determine what service states the flap detection logic will use for this service.'
    )
    retain_status_information = SelectField(
        'Retain status info',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not status-related information about the service is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive.'
    )
    retain_nonstatus_information = SelectField(
        'Retain non-status info',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not non-status information about the service is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive.'
    )

    # Notifications
    notifications_enabled = SelectField(
        'Enable notifications',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not notifications for this service are enabled.'
    )
    contacts = SelectMultipleField(
        'Contacts',
        choices=_listobjects_choices('contact'),
        description='This is a list of the short names of the contacts that should be notified whenever there are problems (or recoveries) with this service. Multiple contacts should be separated by commas. Useful if you want notifications to go to just a few people and don\'t want to configure contact groups. You must specify at least one contact or contact group in each service definition.'
    )
    contact_groups = SelectMultipleField(
        'Contact groups',
        choices=_listobjects_choices('contactgroup'),
        description='This is a list of the short names of the contact groups that should be notified whenever there are problems (or recoveries) with this service. You must specify at least one contact or contact group in each service definition.'
    )
    notification_interval = IntegerField(
        'Notification interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" to wait before re-notifying a contact that this service is still in a non-OK state. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, Shinken will not re-notify contacts about problems for this service - only one problem notification will be sent out.'
    )
    first_notification_delay = IntegerField(
        'First notification delay',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='This directive is used to define the number of "time units" to wait before sending out the first problem notification when this service enters a non-OK state. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, Shinken will start sending out notifications immediately.'
    )
    notification_period = SelectField(
        'Notification period',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short name of the time period during which notifications of events for this service can be sent out to contacts. No service notifications will be sent out during times which is not covered by the time period.'
    )
    notification_options = SelectMultipleField(
        'Notification options',
        choices=[('w','Warning (d)'), ('u','Unknown (u)'), ('c', 'Critical (c)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')],
        description='This directive is used to determine when notifications for the service should be sent out. '
    )

    # Business rules
    business_impact = IntegerField(
        'Business impact',
        validators=[validators.Optional(), validators.NumberRange(0, 5)],
        description='This variable is used to set the importance we gave to this service from the less important (0 = nearly nobody will see if it\'s in error) to the maximum (5 = you lost your job if it fail). The default value is 2.'
    )
    business_rule_output_template = TextField(
        'Business rule output template',
        description='Classic service check output is managed by the underlying plugin (the check output is the plugin stdout). For business rules, as there\'s no real plugin behind, the output may be controlled by a template string defined in business_rule_output_template directive.'
    )
    business_rule_smart_notifications = SelectField(
        'Enable smart notifications',
        choices=_listboolean_choices(),
        description='This variable may be used to activate smart notifications on business rules. This allows to stop sending notification if all underlying problems have been acknowledged.'
    )
    business_rule_downtime_as_ack = SelectField(
        'Include downtimes in smart notifications',
        choices=_listboolean_choices()
    )
    business_rule_host_notification_options = SelectMultipleField(
        'Business rule host notification options',
        choices=[('d','Down (d)'), ('u','Unknown (u)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')],
        description='This option allows to enforce business rules underlying hosts notification options to easily compose a consolidated meta check. This is especially useful for business rules relying on grouping expansion.'
    )
    business_rule_service_notification_options = SelectMultipleField(
        'Business rule service notification options',
        choices=[('w','Warning (w)'), ('u','Unknown (u)'), ('c', 'Critical (c)'), ('r', 'Recovery (r)'), ('f', 'Flapping (f)'), ('s', 'Scheduled downtime starts/ends (s)'), ('n', 'None (n)')],
        description='This option allows to enforce business rules underlying services notification options to easily compose a consolidated meta check. This is especially useful for business rules relying on grouping expansion.'
    )

    # Snapshot
    snapshot_enabled = SelectField(
        'Enable snapshot',
        choices=_listboolean_choices(),
        description='This option allows to enable snapshots snapshots on this element.'
    )
    snapshot_command = SelectField(
        'Snapshot command',
        choices=_listobjects_choices('command', True),
        description='Command to launch when a snapshot launch occurs.'
    )
    snapshot_period = SelectField(
        'Snapshot period',
        choices=_listobjects_choices('timeperiod', True),
        description='Timeperiod when the snapshot call is allowed.'
    )
    snapshot_criteria = SelectMultipleField(
        'Snapshot criteria',
        choices=[('d','Down (d)'),('u','Unknown (u)')],
        description='List of states that enable the snapshot launch. Mainly bad states.'
    )
    snapshot_interval = IntegerField(
        'Snapshot interval',
        validators=[validators.Optional(), validators.NumberRange(0)],
        description='Minimum interval between two launch of snapshots to not hammering the host, in interval_length units (by default 60s)'
    )

    # Misc.
    process_perf_data = SelectField(
        'Process perf data',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the processing of performance data is enabled .'
    )
    stalking_options = SelectMultipleField(
        'Stalking options',
        choices=[('o','Up (o)'), ('d','Down (d)'), ('u','Unknown (u)')],
        description='This directive determines which service states "stalking" is enabled for.'
    )
    duplicate_foreach = TextField(
        'Duplicate for each',
        description='TODO: Advanced mode only?'
    )
    trigger_broker_raise_enabled = SelectField(
        'Enable trigger',
        choices=_listboolean_choices(),
        description='This option define the behavior of the defined trigger (Default 0). If set to 1, this means the trigger will modify the output / return code of the check. If 0, this means the code executed by the trigger does nothing to the check (compute something elsewhere ?) Basically, if you use one of the predefined function (trigger_functions.py) set it to 1'
    )
    trigger_name = TextField(
        'Trigger name',
        description='This options define the trigger that will be executed after a check result (passive or active). This file trigger_name.trig has to exist in the trigger directory or sub-directories.'
    )

class ServiceGroupForm(Form):
    #Description
    servicegroup_name = TextField(
        'ServiceGroup name',
        description='This directive is used to define a short name used to identify the service group.'
    )
    alias = TextField(
        'alias',
        description='This directive is used to define is a longer name or description used to identify the service group. It is provided in order to allow you to more easily identify a particular service group.'
    )
    members = SelectMultipleField(
        'Services',
        choices=_listobjects_choices('services', True),
        description='This is a list of the descriptions of services (and the names of their corresponding hosts) that should be included in this group. This directive may be used as an alternative to the servicegroups directive in service definitions.'
    )
    servicegroup_members = SelectMultipleField(
        'Services',
        choices=_listobjects_choices('servicegroup', True),
        description='This optional directive can be used to include services from other "sub" service groups in this service group. Specify a comma-delimited list of short names of other service groups whose members should be included in this group.'
    )
    notes = TextField(
        'Note string',
        description='This directive is used to define an optional string of notes pertaining to the service group.'
    )
    notes_url = URLField(
        'Notes URL',
        description='This directive is used to define an optional URL that can be used to provide more information about the service group.'
    )
    action_url = URLField(
        'Action URL',
        description='This directive is used to define an optional URL that can be used to provide more actions to be performed on the service group.'
    )

class ContactForm(Form):
    #Description
    contact_name = TextField(
        'Host name',
        description='This directive is used to define a short name used to identify the contact. It is referenced in contact group definitions.'
    )
    alias = TextField(
        u'Alias',
        description='This directive is used to define a longer name or description for the contact.'
    )
    contactgroups = SelectMultipleField(
        'Contact group',
        choices= _listobjects_choices('contactgroup', True),
        description='This directive is used to identify the short name(s) of the contactgroup(s) that the contact belongs to.'
    )
    host_notification_enabled = SelectField(
        'host_notification_enabled',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the contact will receive notifications about host problems and recoveries.'
    )
    service_notification_enabled = SelectField(
        'service_notification_enabled',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the contact will receive notifications about service problems and recoveries.'
    )
    host_notification_period = SelectField(
        'Host notification period',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short name of the time period during which the contact can be notified about host problems or recoveries.'
    )
    service_notification_period = SelectField(
        'Service notification period',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short name of the time period during which the contact can be notified about service problems or recoveries.'
    )
    host_notification_options = SelectMultipleField(
        'Host notification options',
        choices=[('d','d'),('u','u'),('r','r'),('f','f'),('s','s'),('n','n')],
        description='This directive is used to define the host states for which notifications can be sent out to this contact.'
    )
    service_notification_options = SelectMultipleField(
        'Service notification options',
        choices=[('w','w'),('u','u'),('c','c'),('r','r'),('f','f'),('s','s'),('n','n')],
        description='This directive is used to define the service states for which notifications can be sent out to this contact.'
    )
    host_notification_commands = TextField(
        'Host notification command',
        description='This directive is used to define a list of the short names of the commands used to notify the contact of a host problem or recovery. Multiple notification commands should be separated by commas. All notification commands are executed when the contact needs to be notified.'
    )
    server_notification_commands = TextField(
        'Service notification command',
        description='This directive is used to define a list of the short names of the commands used to notify the contact of a service problem or recovery. Multiple notification commands should be separated by commas.'
    )
    email = TextField(
        'Email',
        description='This directive is used to define an email address for the contact.'
    )
    pager = TextField(
        'Pager',
        description='This directive is used to define a pager number for the contact. It can also be an email address to a pager gateway.'
    )
    addressx = TextField(
        'additional_contact_address',
        description='Address directives are used to define additional "addresses" for the contact. These addresses can be anything - cell phone numbers, instant messaging addresses, etc. Depending on how you configure your notification commands.'
    )
    can_submit_commands = SelectField(
        'can_submit_commands',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not the contact can submit external commands to Shinken from the CGIs.'
    )
    retain_status_information = SelectField(
        'retain_status_information',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not status-related information about the contact is retained across program restarts.'
    )
    retain_nonstatus_information = SelectField(
        'retain_nonstatus_information',
        choices=_listboolean_choices(),
        description='This directive is used to determine whether or not non-status information about the contact is retained across program restarts. '
    )
    min_business_impact = IntegerField(
        'Minimum business impact',
        description='This directive is use to define the minimum business criticity level of a service/host the contact will be notified.'
    )

class ContactGroupForm(Form):
    #Description
    contactgroup_name = TextField(
        'Host name',
        description='This directive is a short name used to identify the contact group.'
    )
    alias = TextField(
        u'Alias',
        description='This directive is used to define a longer name or description used to identify the contact group.'
    )
    #Members
    members = SelectMultipleField(
        'Members',
        choices=_listobjects_choices('contact', True),
        description='This directive is used to define a list of the short names of contacts that should be included in this group.'
    )
    contactgroup_members = SelectMultipleField(
        'Contact groups members',
        choices=_listobjects_choices('contactgroup', True),
        description='This optional directive can be used to include contacts from other "sub" contact groups in this contact group.'
    )

class TimeperiodForm(Form):
    #Description
    timeperiod_name = TextField(
        'Timeperiod name',
        description='This directives is the short name used to identify the time period.'
    )
    alias = TextField(
        'Alias',
        description='This directive is a longer name or description used to identify the time period.'
    )
    exclude = SelectMultipleField(
        'Excluded timeperiods',
        choices=_listobjects_choices('timeperiod', True),
        description='This directive is used to specify the short names of other timeperiod definitions whose time ranges should be excluded from this timeperiod.'
    )
    #weekdays
    sunday = TextField('Sunday', default= '00:00-00:00')
    monday = TextField('Monday', default= '00:00-00:00')
    tuesday = TextField('Tuesday', default= '00:00-00:00')
    wednesday = TextField('Wednesday', default= '00:00-00:00')
    thursday = TextField('Thursday', default= '00:00-00:00')
    friday = TextField('Friday', default= '00:00-00:00')
    saturday = TextField('Saturday', default= '00:00-00:00')

class CommandForm(Form):
    #Description
    command_name = TextField(
        'Command name',
        description='This directive is the short name used to identify the command. It is referenced in contact, host, and service definitions (in notification, check, and event handler directives), among other places.'
    )
    command_line = TextField(
        'Command line',
        description='This directive is used to define what is actually executed by Shinken when the command is used for service or host checks, notifications, or event handlers. Before the command line is executed, all valid macros are replaced with their respective values.'
    )
    poller_tag = TextField(
        'Poller tag',
        description='This directive is used to define the poller_tag of this command. If the host/service that call this command do not override it with their own poller_tag, it will make this command if used in a check only taken by polelrs that also have this value in their poller_tags parameter. By default there is no poller_tag, so all untagged pollers can take it.'
    ) # TODO : Show a list of existing tags + 'None' ?
