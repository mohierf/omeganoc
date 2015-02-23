/*
 * This file is part of Omega Noc
 * Copyright Omega Noc (C) 2015 Omega Cube and contributors
 * Xavier Roger-Machart, xrm@omegacube.fr
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
define(['jquery', 'onoc.createurl', 'datatables'], function(jQuery, createurl) {
    "use strict";
    
    // Types (prefixed with * if several values possible) :
    // - shortname (unique identifier, like host name, service name etc...)
    // - string
    // - url
    // - bool (0/1)
    // - integer
    // - address (ip, domain, ... of a host)
    // - enum[id:desc,id:desc,...]
    
    // Properties used on host objects
    var host_properties = {
        'host_name': {
            'name': 'host_name',
            'is_required': true,
            'description': 'A short name used to identify the host',
            'type': 'shortname'},
        'alias': {
            'name': 'alias',
            'is_required': true,
            'description': 'A longer name or description used to identify the host',
            'type': 'string'},
        'display_name': {
            'name': 'display_name',
            'is_required': false,
            'description': 'An alternate name that should be displayed in the interfaces for this host',
            'type': 'string'},
        'address': {
            'name': 'address',
            'is_required': true,
            'description': 'The address of the host. Normally, this is an IP address, although it could really be anything you want (so long as it can be used to check the status of the host).',
            'type': 'address'},
        'parents': {
            'name': 'parents',
            'is_required': false,
            'description': ' Parent hosts are typically routers, switches, firewalls, etc. that lie between the monitoring host and a remote hosts. A router, switch, etc. which is closest to the remote host is considered to be that host\'s "parent". If this host is on the same network segment as the host doing the monitoring (without any intermediate routers, etc.) the host is considered to be on the local network and will not have a parent host. Leave this value blank if the host does not have a parent host (i.e. it is on the same segment as the host). The order in which you specify parent hosts has no effect on how things are monitored.',
            'type': '*host'},
        'hostgroups': {
            'name': 'hostgroups',
            'is_required': false,
            'description': 'Identifies the hostgroup(s) that the host belongs to. This directive may be used as an alternative to (or in addition to) using the members directive in hostgroup definitions.',
            'type': '*hostgroup'},
        'check_command': {
            'name': 'check_command',
            'is_required': false,
            'description': 'The command that should be used to check if the host is up or down',
            'type': 'command'},
        'initial_state': {
            'name': 'initial_state',
            'is_required': false,
            'description': 'Defines a longer name or description used to identify the host',
            'default': 'o',
            'type': 'enum[o:Up,d:Down,u:Unreachable]'},
        'max_check_attempts': {
            'name': 'max_check_attempts',
            'is_required': true,
            'description': 'Number of times that Nagios will retry the host check command if it returns any state other than an OK state',
            'type': 'integer'},
        'check_interval': {
            'name': 'check_interval',
            'is_required': false,
            'default': '1',
            'description': 'Number of "time units" between regularly scheduled checks of the host. By default a time unit is 60 seconds, until it has been changed in the global configuration.',
            'type': 'integer'},
        'retry_interval': {
            'name': 'retry_interval',
            'is_required': false,
            'description': 'Number of "time units" to wait before scheduling a re-check of the hosts. By default a time unit is 60 seconds, until it has been changed in the global configuration.  Hosts are rescheduled at the retry interval when they have changed to a non-UP state. Once the host has been retried max_check_attempts times without a change in its status, it will revert to being scheduled at its "normal" rate as defined by the check_interval value.',
            'type': 'integer'},
        'active_checks_enabled': {
            'name': 'active_checks_enabled',
            'is_required': false,
            'description': 'Determines whether or not active checks (either regularly scheduled or on-demand) of this host are enabled',
            'default': '1',
            'type': 'bool'},
        'passive_checks_enabled': {
            'name': 'passive_checks_enabled',
            'is_required': false,
            'description': 'Determines whether or not passive checks are enabled for this host',
            'default': '1',
            'type': 'bool'},
        'check_period': {
            'name': 'check_period',
            'is_required': true,
            'description': 'Time period during which active checks of this host can be made',
            'type': 'timeperiod'},
        'obsess_over_host': {
            'name': 'obsess_over_host',
            'is_required': false,
            'description': 'Determines whether or not checks for the host will be "obsessed" over using the ochp_command',
            'type': 'bool'},
        'check_freshness': {
            'name': 'check_freshness',
            'is_required': false,
            'description': 'Determines whether or not freshness checks are enabled for this host',
            'default': '1',
            'type': 'bool'},
        'freshness_threshold': {
            'name': 'freshness_threshold',
            'is_required': false,
            'description': 'Freshness threshold (in seconds) for this host',
            'type': 'integer'},
        'event_handler': {
            'name': 'event_handler',
            'is_required': false,
            'description': 'Command that should be run whenever a change in the state of the host is detected (i.e. whenever it goes down or recovers). The maximum amount of time that the event handler command can run is controlled by the event_handler_timeout option.',
            'type': 'command'},
        'event_handler_enabled': {
            'name': 'event_handler_enabled',
            'is_required': false,
            'description': 'Determines whether or not the event handler for this host is enabled',
            'type': 'bool'},
        'low_flap_threshold': {
            'name': 'low_flap_threshold',
            'is_required': false,
            'description': 'Low state change threshold used in flap detection for this host. If you set this directive to a value of 0, the program-wide value specified by the low_host_flap_threshold directive will be used.',
            'type': 'integer'},
        'high_flap_threshold': {
            'name': 'high_flap_threshold',
            'is_required': false,
            'description': 'High state change threshold used in flap detection for this host. If you set this directive to a value of 0, the program-wide value specified by the high_host_flap_threshold directive will be used.',
            'type': 'integer'},
        'flap_detection_enabled': {
            'name': 'flap_detection_enabled',
            'is_required': false,
            'description': 'Determines whether or not flap detection is enabled for this host',
            'type': 'bool'},
        'flap_detection_options': {
            'name': 'flap_detection_options',
            'is_required': false,
            'description': 'Host states the flap detection logic will use for this host',
            'type': '*enum[o:Up,d:Down,u:Unreachable]'},
        'process_perf_data': {
            'name': 'process_perf_data',
            'is_required': false,
            'description': 'Determine whether or not the processing of performance data is enabled for this host',
            'type': 'bool'},
        'retain_status_information': {
            'name': 'retain_status_information',
            'is_required': false,
            'description': 'Determines whether or not status-related information about the host is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive.',
            'type': 'bool'},
        'retain_nonstatus_information': {
            'name': 'retain_nonstatus_information',
            'is_required': false,
            'description': 'Determines whether or not non-status information about the host is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive.',
            'type': 'bool'},
        'contacts': {
            'name': 'contacts',
            'is_required': true,
            'description': 'Contacts that should be notified whenever there are problems (or recoveries) with this host. Useful if you want notifications to go to just a few people and don\'t want to configure contact groups. You must specify at least one contact or contact group in each host definition.',
            'type': '*contact'},
        'contact_groups': {
            'name': 'contact_groups',
            'is_required': true,
            'description': 'Contact groups that should be notified whenever there are problems (or recoveries) with this host. You must specify at least one contact or contact group in each host definition.',
            'type': '*contactgroup'},
        'notification_interval': {
            'name': 'notification_interval',
            'is_required': true,
            'description': 'Number of "time units" to wait before re-notifying a contact that this service is still down or unreachable. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, Nagios will not re-notify contacts about problems for this host - only one problem notification will be sent out.',
            'type': 'integer'},
        'first_notification_delay': {
            'name': 'first_notification_delay',
            'is_required': false,
            'description': 'Number of "time units" to wait before sending out the first problem notification when this host enters a non-UP state. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, Nagios will start sending out notifications immediately.',
            'type': 'integer'},
        'notification_period': {
            'name': 'notification_period',
            'is_required': true,
            'description': 'Time period during which notifications of events for this host can be sent out to contacts. If a host goes down, becomes unreachable, or recoveries during a time which is not covered by the time period, no notifications will be sent out.',
            'type': 'timeperiod'},
        'notification_options': {
            'name': 'notification_options',
            'is_required': false,
            'description': 'Determines when notifications for the host should be sent out. Valid options are a combination of one or more of the following: DOWN state, UNREACHABLE state, recoveries (OK state), host starts and stops flapping, and when scheduled downtime starts and ends. If you specify None as an option, no host notifications will be sent out. If you do not specify any notification options, the monitoring system will assume that you want notifications to be sent out for all possible states. Example: If you specify "Down Recover" in this field, notifications will only be sent out when the host goes DOWN and when it recovers from a DOWN state.',
            'type': '*enum[d:Down,u:Unreachable,r:Recovery,f:Flapping,s:Scheduled downtime,n:None]'},
        'notifications_enabled': {
            'name': 'notifications_enabled',
            'is_required': false,
            'description': 'Determines whether or not notifications for this host are enabled',
            'type': 'bool'},
        'stalking_options': {
            'name': 'stalking_options',
            'is_required': false,
            'description': 'Determines which host states "stalking" is enabled for',
            'type': 'enum[o:Up,d:Down,u:Unreachable]'},
        'notes': {
            'name': 'notes',
            'is_required': false,
            'description': 'Notes pertaining to the host',
            'type': 'string'},
        'notes_url': {
            'name': 'notes_url',
            'is_required': false,
            'description': 'URL that can be used to provide more information about the host',
            'type': 'url'},
        'action_url': {
            'name': 'action_url',
            'is_required': false,
            'description': 'URL that can be used to provide more actions to be performed on the host',
            'type': 'url'},
    };
    
    // Properties used on hostgroup objects
    var hostgroup_properties = {
        'hostgroup_name': {
            'name': 'hostgroup_name',
            'is_required': true,
            'description': 'A short name used to identify the host group',
            'type': 'shortname'},
        'alias': {
            'name': 'alias',
            'is_required': false,
            'description': 'A longer name or description used to identify the host group',
            'type': 'string'},
        'members': {
            'name': 'members',
            'is_required': false,
            'description': 'List of hosts that should be included in this group',
            'type': '*host'},
        'hostgroup_members': {
            'name': 'hostgroup_members',
            'is_required': false,
            'description': 'Can be used to include hosts from other "sub" host groups in this host group',
            'type': '*hostgroup'},
        'notes': {
            'name': 'notes',
            'is_required': false,
            'description': 'An optional string of notes pertaining to the host',
            'type': 'string'},
        'notes_url': {
            'name': 'notes_url',
            'is_required': false,
            'description': 'An optional URL that can be used to provide more information about the host group',
            'type': 'url'},
        'action_url': {
            'name': 'action_url',
            'is_required': false,
            'description': 'An optional URL that can be used to provide more actions to be performed on the host group',
            'type': 'url'},
    };
    
    var structure = {
        'host': { 
          'id': 'host',
          'name': 'Host',
          'names': 'Hosts',
          'description': 'Defines a physical server, workstation, device, etc. that resides on your network',
          'key': 'host_name',
          'properties': host_properties},
        'hostgroup': { 
          'id': 'hostgroup',
          'name': 'Host group',
          'names': 'Host groups',
          'description': 'Groups several hosts in a single entity',
          'key': 'hostgroup_name',
          'properties': hostgroup_properties},
    };
    
    function configurationObject(nagData) {
        this._attributes = nagData;
        this._meta = nagData.meta;
        delete this._attributes.meta;

        this._isDirty = false; // true is the object is changed and not saved yet
        this._changes = {};
    }
    
    configurationObject.prototype = {
        'isTemplate': function() {
            return 'name' in this.attributes;
        },
        
        'export': function() {
            // Generates an object in the nag format, ready to be sent back to the server
            var meta = {};
            meta.object_type = this.getObjectType();
            meta.id = this._attributes[structure[type].key];
            meta.name = this._attributes.name;
            
            return jQuery.extend({'meta': meta}, this._changes);
        },
        
        'getAttribute': function(name) {
            // Gets the value of the specified attribute
            return this._attribute[name];
        },
        
        'getAttributeInherited': function(name) {
            return this._meta.inherited_attributes[name];
        },
        
        'setAttribute': function(name, value) {
            // Sets the value of the specified attribute
            // If the value is undefined or null, the attribute gets removed
            if(!value)
                value = null;
            
            var old = name in this._attributes ? this._attributes[name] : null;
            
            if(value != old) {
                if(value == null) {
                    // Remove the attribute
                    delete this._attributes[name];
                }
                else {
                    this._attributes[name] = value;
                }
                
                this._isDirty = true;
                return true;
            }
            else {
                return false;
            }
        },
        
        'getAttributeNames': function() {
            return Object.keys(this._attributes);
        },
        
        'getFilename': function() {
            return this._meta.filename;
        },
        
        'getObjectType': function() {
            this._meta.object_type;
        },
    };
    
    jQuery(function() {
        var table = jQuery('#config_main_list');
        
        table.dataTable({
            'ajax': 'http://192.168.33.101:5000/config/hosts',
            'columns': [
                { 'title': 'Host name', 'data': 'host_name' },
                { 'title': 'Address', 'data': 'address' },
                { 'title': 'File', 'data': 'meta.filename' },
            ],
        });
    });
});