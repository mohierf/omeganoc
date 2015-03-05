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
define([], function() {
    "use strict";
    
    // Types (prefixed with * if several values possible) :
    // - shortname (unique identifier, like host name, service name etc...)
    // - string
    // - url
    // - email
    // - bool (0/1)
    // - integer
    // - address (ip, domain, ... of a host)
    // - enum[id:desc,id:desc,...]
    
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
            'description': 'By default Nagios will assume that all hosts are in UP states when it starts. You can override the initial state for a host by using this directive.',
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
        'realm': {
            'name': 'realm',
            'is_required': false,
            'description': '',
            'type': 'realm'},
        'poller_tag': {
            'name': 'poller_tag',
            'is_required': false,
            'description': '',
            'type': 'string'},
        'business_impact': {
            'name': 'business_impact',
            'is_required': false,
            'description': '',
            'type': 'integer'},
        'resultmodulations': {
            'name': 'resultmodulations',
            'is_required': false,
            'description': '',
            'type': '*resultmodulation'},
        'escalations': {
            'name': 'escalations',
            'is_required': false,
            'description': '',
            'type': '*escalation'},
        'business_impact_modulations': {
            'name': 'business_impact_modulations',
            'is_required': false,
            'description': '',
            'type': '*businessimpactmodulation'},
        'maintenance_period': {
            'name': 'maintenance_period',
            'is_required': false,
            'description': '',
            'type': 'timeperiod'},
        'service_overrides': {
            'name': 'service_overrides',
            'is_required': false,
            'description': '',
            'type': 'string'},
        'service_excludes': {
            'name': 'service_excludes',
            'is_required': false,
            'description': '',
            'type': '*service'},
        'labels': {
            'name': 'labels',
            'is_required': false,
            'description': '',
            'type': 'string'},
        'business_rule_output_template': {
            'name': 'business_rule_output_template',
            'is_required': false,
            'description': '',
            'type': 'string'},
        'business_rule_smart_notifications': {
            'name': 'business_rule_smart_notifications',
            'is_required': false,
            'description': '',
            'type': 'bool'},
        'business_rule_downtime_as_ack': {
            'name': 'business_rule_downtime_as_ack',
            'is_required': false,
            'description': '',
            'type': 'bool'},
        'business_rule_host_notification_options': {
            'name': 'business_rule_host_notification_options',
            'is_required': false,
            'description': '',
            'type': '*enum[d:Down,u:Unreachable,r:Recovery,f:Flapping,s:Scheduled downtime,n:None]'},
        'business_rule_service_notification_options': {
            'name': 'business_rule_service_notification_options',
            'is_required': false,
            'description': '',
            'type': '*enum[w:Warning,u:Unknown,c:Critical,r:Recovery,f:Flapping,s:Scheduled downtime,n:None]'},
        'snapshot_enabled': {
            'name': 'snapshot_enabled',
            'is_required': false,
            'description': '',
            'type': 'bool'},
        'snapshot_command': {
            'name': 'snapshot_command',
            'is_required': false,
            'description': '',
            'type': 'command'},
        'snapshot_period': {
            'name': 'snapshot_period',
            'is_required': false,
            'description': '',
            'type': 'timeperiod'},
        'snapshot_criteria': {
            'name': 'snapshot_criteria',
            'is_required': false,
            'description': '',
            'type': '*enum[d:Down,u:Unreachable]'},
        'snapshot_interval': {
            'name': 'snapshot_interval',
            'is_required': false,
            'description': '',
            'type': 'integer'},
        'trigger_name': {
            'name': 'trigger_name',
            'is_required': false,
            'description': '',
            'type': 'string'},
        'trigger_broker_raise_enabled': {
            'name': 'trigger_broker_raise_enabled',
            'is_required': false,
            'description': '',
            'type': 'bool'},
    };
    
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
    
    var service_properties = {
        'host_name': {
            'name': 'host_name',
            'is_required': true,
            'description': 'The host(s) that the service "runs" on or is associated with',
            'type': '*host'},
        'hostgroup_name': {
            'name': 'hostgroup_name',
            'is_required': false,
            'description': 'The hostgroup(s) that the service "runs" on or is associated with',
            'type': '*hostgroup'},
        'service_description': {
            'name': 'service_description',
            'is_required': true,
            'description': 'Description of the service, which may contain spaces, dashes, and colons (semicolons, apostrophes, and quotation marks should be avoided). No two services associated with the same host can have the same description. Services are uniquely identified with their host_name and service_description directives.',
            'type': 'shortname'},
        'display_name': {
            'name': 'display_name',
            'is_required': false,
            'description': 'An alternate name that should be displayed in the web interface for this service',
            'type': 'string'},
        'servicegroups': {
            'name': 'servicegroups',
            'is_required': false,
            'description': 'Identify the servicegroup(s) that the service belongs to. This directive may be used as an alternative to using the members directive in servicegroup definitions.',
            'type': '*servicegroup'},
        'is_volatile': {
            'name': 'is_volatile',
            'is_required': false,
            'description': 'Denotes whether the service is "volatile"',
            'default': '0',
            'type': 'bool'},
        'check_command': {
            'name': 'check_command',
            'is_required': true,
            'description': 'Command that will be run in order to check the status of the service. The maximum amount of time that the service check command can run is controlled by the service_check_timeout option.',
            'type': 'command'},
        'initial_state': {
            'name': 'initial_state',
            'is_required': false,
            'description': 'By default the monitoring system will assume that all services are in OK states when it starts. You can override the initial state for a service by using this directive.',
            'type': 'enum[o:Ok,w:Warning,u:Unknown,c:Critical]'},
        'max_check_attempts': {
            'name': 'max_check_attempts',
            'is_required': true,
            'description': 'Number of times that the service check command will be re-run if it returns any state other than an OK state. Setting this value to 1 will generate an alert without retrying the service check again.',
            'type': 'integer'},
        'check_interval': {
            'name': 'check_interval',
            'is_required': true,
            'description': 'Number of "time units" to wait before scheduling the next "regular" check of the service. "Regular" checks are those that occur when the service is in an OK state or when the service is in a non-OK state, but has already been rechecked max_check_attempts number of times. Unless you\'ve changed the interval_length global directive from the default value of 60, this number will mean minutes.',
            'type': 'integer'},
        'retry_interval': {
            'name': 'retry_interval',
            'is_required': true,
            'description': 'Number of "time units" to wait before scheduling a re-check of the service. Services are rescheduled at the retry interval when they have changed to a non-OK state. Once the service has been retried max_check_attempts times without a change in its status, it will revert to being scheduled at its "normal" rate as defined by the check_interval value. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes.',
            'type': 'integer'},
        'active_checks_enabled': {
            'name': 'active_checks_enabled',
            'is_required': false,
            'description': 'Determines whether or not active checks of this service are enabled',
            'default': '1',
            'type': 'bool'},
        'passive_checks_enabled': {
            'name': 'passive_checks_enabled',
            'is_required': false,
            'description': 'Determines whether or not passive checks of this service are enabled',
            'default': '1',
            'type': 'bool'},
        'check_period': {
            'name': 'check_period',
            'is_required': true,
            'description': 'Time period during which active checks of this service can be made',
            'type': 'timeperiod'},
        'obsess_over_service': {
            'name': 'obsess_over_service',
            'is_required': false,
            'description': 'Determines whether or not checks for the service will be "obsessed" over using the ocsp_command',
            'type': 'bool'},
        'check_freshness': {
            'name': 'check_freshness',
            'is_required': false,
            'description': 'Determines whether or not freshness checks are enabled for this service.',
            'default': '1',
            'type': 'bool'},
        'freshness_threshold': {
            'name': 'freshness_threshold',
            'is_required': false,
            'description': 'Freshness threshold (in seconds) for this service. If you set this directive to a value of 0, a freshness threshold will be determined automatically.',
            'type': 'integer'},
        'event_handler': {
            'name': 'event_handler',
            'is_required': false,
            'description': 'Command that should be run whenever a change in the state of the service is detected (i.e. whenever it goes down or recovers). The maximum amount of time that the event handler command can run is controlled by the event_handler_timeout option. ',
            'type': 'command'},
        'event_handler_enabled': {
            'name': 'event_handler_enabled',
            'is_required': false,
            'description': 'Determines whether or not the event handler for this service is enabled',
            'type': 'bool'},
        'low_flap_threshold': {
            'name': 'low_flap_threshold',
            'is_required': false,
            'description': 'Low state change threshold used in flap detection for this service. If you set this directive to a value of 0, the program-wide value specified by the low_service_flap_threshold directive will be used.',
            'type': 'integer'},
        'high_flap_threshold': {
            'name': 'high_flap_threshold',
            'is_required': false,
            'description': 'High state change threshold used in flap detection for this service. If you set this directive to a value of 0, the program-wide value specified by the high_service_flap_threshold directive will be used.',
            'type': 'integer'},
        'flap_detection_enabled': {
            'name': 'flap_detection_enabled',
            'is_required': false,
            'description': 'Determines whether or not flap detection is enabled for this service',
            'type': 'bool'},
        'flap_detection_options': {
            'name': 'flap_detection_options',
            'is_required': false,
            'description': 'Determines what service states the flap detection logic will use for this service',
            'type': '*enum[o:Ok,w:Warning,c:Critical,u:Unreachable]'},
        'process_perf_data': {
            'name': 'process_perf_data',
            'is_required': false,
            'description': 'Determines whether or not the processing of performance data is enabled for this service',
            'type': 'bool'},
        'retain_status_information': {
            'name': 'retain_status_information',
            'is_required': false,
            'description': 'Determines whether or not status-related information about the service is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive.',
            'type': 'bool'},
        'retain_nonstatus_information': {
            'name': 'retain_nonstatus_information',
            'is_required': false,
            'description': 'Determines whether or not non-status information about the service is retained across program restarts. This is only useful if you have enabled state retention using the retain_state_information directive.',
            'type': 'bool'},
        'notification_interval': {
            'name': 'notification_interval',
            'is_required': true,
            'description': 'Number of "time units" to wait before re-notifying a contact that this service is still in a non-OK state. Unless you\'ve changed the interval_length system directive from the default value of 60, this number will mean minutes. If you set this value to 0, we will not re-notify contacts about problems for this service - only one problem notification will be sent out.',
            'type': 'integer'},
        'first_notification_delay': {
            'name': 'first_notification_delay',
            'is_required': false,
            'description': 'Number of "time units" to wait before sending out the first problem notification when this service enters a non-OK state. Unless you\'ve changed the interval_length directive from the default value of 60, this number will mean minutes. If you set this value to 0, we will start sending out notifications immediately.',
            'type': 'integer'},
        'notification_period': {
            'name': 'notification_period',
            'is_required': true,
            'description': 'Time period during which notifications of events for this service can be sent out to contacts. No service notifications will be sent out during times which is not covered by the time period.',
            'type': 'timeperiod'},
        'notification_options': {
            'name': 'notification_options',
            'is_required': false,
            'description': 'Determines when notifications for the service should be sent out. Valid options are a combination of one or more of the following: send notifications on a WARNING state, on an UNKNOWN state, on a CRITICAL state, on recoveries (OK state), when the service starts and stops flapping, and when scheduled downtime starts and ends. If you specify None as an option, no service notifications will be sent out. If you do not specify any notification options, we will assume that you want notifications to be sent out for all possible states.',
            'type': '*enum[w:Warning,u:Unknown,c:Critical,r:Recovery,f:Flapping,s:Scheduled downtime]'},
        'notifications_enabled': {
            'name': 'notifications_enabled',
            'is_required': false,
            'description': 'Determines whether or not notifications for this service are enabled',
            'type': 'bool'},
        'contacts': {
            'name': 'contacts',
            'is_required': true,
            'description': 'Contacts that should be notified whenever there are problems (or recoveries) with this service. Useful if you want notifications to go to just a few people and don\'t want to configure contact groups. You must specify at least one contact or contact group in each service definition.',
            'type': '*contact'},
        'contact_groups': {
            'name': 'contact_groups',
            'is_required': true,
            'description': 'Contact groups that should be notified whenever there are problems (or recoveries) with this service. You must specify at least one contact or contact group in each service definition.',
            'type': '*contactgroup'},
        'stalking_options': {
            'name': 'stalking_options',
            'is_required': false,
            'description': 'Determines which service states "stalking" is enabled for',
            'type': '*enum[o:Ok,w:Warning,u:Unknown,c:Critical]'},
        'notes': {
            'name': 'notes',
            'is_required': false,
            'description': 'An optional string of notes pertaining to the service',
            'type': 'string'},
        'notes_url': {
            'name': 'notes_url',
            'is_required': false,
            'description': 'An optional URL that can be used to provide more information about the service',
            'type': 'url'},
        'action_url': {
            'name': 'action_url',
            'is_required': false,
            'description': 'An optional URL that can be used to provide more actions to be performed on the service',
            'type': 'url'},
    };
    
    var servicegroup_properties = {
        'servicegroup_name': {
            'name': 'servicegroup_name',
            'is_required': true,
            'description': 'A short name used to identify the service group',
            'type': 'shortname'},
        'alias': {
            'name': 'alias',
            'is_required': true,
            'description': 'A longer name or description used to identify the service group. It is provided in order to allow you to more easily identify a particular service group.',
            'type': 'string'},
        'members': {
            'name': 'members',
            'is_required': false,
            'description': 'Descriptions of services (and the names of their corresponding hosts) that should be included in this group. This directive may be used as an alternative to the servicegroups directive in service definitions. The format of the member directive is as follows (note that a host name must precede a service name/description): <host1> <service1> <host2> <service2> ... <hostN> <serviceN>',
            'type': '*service|host'},
        'servicegroup_members': {
            'name': 'servicegroup_members',
            'is_required': false,
            'description': 'Can be used to include services from other "sub" service groups in this service group',
            'type': '*servicegroup'},
        'notes': {
            'name': 'notes',
            'is_required': false,
            'description': 'An optional string of notes pertaining to the service group',
            'type': 'string'},
        'notes_url': {
            'name': 'notes_url',
            'is_required': false,
            'description': 'An optional URL that can be used to provide more information about the service group',
            'type': 'url'},
        'action_url': {
            'name': 'action_url',
            'is_required': false,
            'description': 'An optional URL that can be used to provide more actions to be performed on the service group',
            'type': 'url'},
    };
    
    var contact_properties = {
        'contact_name': {
            'name': 'contact_name',
            'is_required': true,
            'description': 'A short name used to identify the contact. It is referenced in contact group definitions. Under the right circumstances, the $CONTACTNAME$ macro will contain this value.',
            'type': 'shortname'},
        'alias': {
            'name': 'alias',
            'is_required': false,
            'description': 'A longer name or description for the contact. Under the rights circumstances, the $CONTACTALIAS$ macro will contain this value. If not specified, the contact_name will be used as the alias.',
            'type': 'string'},
        'contactgroups': {
            'name': 'contactgroups',
            'is_required': false,
            'description': 'Contactgroup(s) that the contact belongs to. This directive may be used as an alternative to (or in addition to) using the members directive in contactgroup definitions.',
            'type': '*contactgroup'},
        'host__notifications_enabled': {
            'name': 'host_notifications_enabled',
            'is_required': true,
            'description': 'Determines whether or not the contact will receive notifications about host problems and recoveries',
            'type': 'bool'},
        'service_notifications_enabled': {
            'name': 'service_notifications_enabled',
            'is_required': true,
            'description': 'Determines whether or not the contact will receive notifications about service problems and recoveries',
            'type': 'bool'},
        'host_notification_period': {
            'name': 'host_notification_period',
            'is_required': true,
            'description': 'Time period during which the contact can be notified about host problems or recoveries. You can think of this as an "on call" time for host notifications for the contact.',
            'type': 'timeperiod'},
        'service_notification_period': {
            'name': 'service_notification_period',
            'is_required': true,
            'description': 'Time period during which the contact can be notified about service problems or recoveries. You can think of this as an "on call" time for service notifications for the contact.',
            'type': 'timeperiod'},
        'host_notification_options': {
            'name': 'host_notification_options',
            'is_required': true,
            'description': 'Defines the host states for which notifications can be sent out to this contact',
            'type': '*enum[d:Down,u:Unreachable,r:Recovery,f:Flapping,s:Down,n:None]'},
        'service_notification_options': {
            'name': 'service_notification_options',
            'is_required': true,
            'description': 'Defines the service states for which notifications can be sent out to this contact',
            'type': '*enum[w:Warning,u:Unknown,c:Critical,r:Recovery,f:Flapping,n:None]'},
        'host_notification_commands': {
            'name': 'host_notification_commands',
            'is_required': true,
            'description': 'Commands used to notify the contact of a host problem or recovery. All notification commands are executed when the contact needs to be notified. The maximum amount of time that a notification command can run is controlled by the notification_timeout option.',
            'type': '*command'},
        'service_notification_commands': {
            'name': 'service_notification_commands',
            'is_required': true,
            'description': 'Commands used to notify the contact of a service problem or recovery. All notification commands are executed when the contact needs to be notified. The maximum amount of time that a notification command can run is controlled by the notification_timeout option.',
            'type': '*command'},
        'email': {
            'name': 'email',
            'is_required': false,
            'description': 'An email address for the contact. Depending on how you configure your notification commands, it can be used to send out an alert email to the contact. Under the right circumstances, the $CONTACTEMAIL$ macro will contain this value.',
            'type': 'email'},
        'pager': {
            'name': 'pager',
            'is_required': false,
            'description': 'A pager number for the contact. It can also be an email address to a pager gateway (i.e. pagejoe@pagenet.com). Depending on how you configure your notification commands, it can be used to send out an alert page to the contact. Under the right circumstances, the $CONTACTPAGER$ macro will contain this value.',
            'type': 'string'},
        'address1': {
            'name': 'address1',
            'is_required': false,
            'description': 'Defines an additional "address" for the contact. This address can be anything - cell phone number, instant messaging address, etc. Depending on how you configure your notification commands, it can be used to send out an alert to the contact. The $CONTACTADDRESS1$ macro will contain this value.',
            'type': 'string'},
        'address2': {
            'name': 'address2',
            'is_required': false,
            'description': 'Defines an additional "address" for the contact. This address can be anything - cell phone number, instant messaging address, etc. Depending on how you configure your notification commands, it can be used to send out an alert to the contact. The $CONTACTADDRESS2$ macro will contain this value.',
            'type': 'string'},
        'address3': {
            'name': 'address3',
            'is_required': false,
            'description': 'Defines an additional "address" for the contact. This address can be anything - cell phone number, instant messaging address, etc. Depending on how you configure your notification commands, it can be used to send out an alert to the contact. The $CONTACTADDRESS3$ macro will contain this value.',
            'type': 'string'},
        'address4': {
            'name': 'address4',
            'is_required': false,
            'description': 'Defines an additional "address" for the contact. This address can be anything - cell phone number, instant messaging address, etc. Depending on how you configure your notification commands, it can be used to send out an alert to the contact. The $CONTACTADDRESS4$ macro will contain this value.',
            'type': 'string'},
        'address5': {
            'name': 'address5',
            'is_required': false,
            'description': 'Defines an additional "address" for the contact. This address can be anything - cell phone number, instant messaging address, etc. Depending on how you configure your notification commands, it can be used to send out an alert to the contact. The $CONTACTADDRESS5$ macro will contain this value.',
            'type': 'string'},
        'address6': {
            'name': 'address6',
            'is_required': false,
            'description': 'Defines an additional "address" for the contact. This address can be anything - cell phone number, instant messaging address, etc. Depending on how you configure your notification commands, it can be used to send out an alert to the contact. The $CONTACTADDRESS6$ macro will contain this value.',
            'type': 'string'},
        'can_submit_commands': {
            'name': 'can_submit_commands',
            'is_required': false,
            'description': 'Determines whether or not the contact can submit external commands from the web interface',
            'default': '0',
            'type': 'bool'},
        'retain_status_information': {
            'name': 'retain_status_information',
            'is_required': false,
            'description': 'Determines whether or not status-related information about the contact is retained across program restarts',
            'type': 'bool'},
        'retain_nonstatus_information': {
            'name': 'retain_nonstatus_information',
            'is_required': false,
            'description': 'Determines whether or not non-status information about the contact is retained across program restarts',
            'type': 'bool'},
    };
    
    var contactgroup_properties = {
        'contactgroup_name': {
            'name': 'contactgroup_name',
            'is_required': true,
            'description': 'A short name used to identify the contact group',
            'type': 'shortname'},
        'alias': {
            'name': 'alias',
            'is_required': true,
            'description': 'A longer name or description used to identify the contact group',
            'type': 'string'},
        'members': {
            'name': 'members',
            'is_required': false,
            'description': 'List of contacts that should be included in this group. This directive may be used as an alternative to (or in addition to) using the contactgroups directive in contact definitions.',
            'type': '*contact'},
        'contactgroup_members': {
            'name': 'contactgroup_members',
            'is_required': false,
            'description': 'Can be used to include contacts from other "sub" contact groups in this contact group',
            'type': '*contactgroup'},
    };
    
    var timeperiod_properties = {
        'timeperiod_name': {
            'name': 'timeperiod_name',
            'is_required': true,
            'description': 'The short name used to identify the time period',
            'type': 'shortname'},
        'alias': {
            'name': 'alias',
            'is_required': true,
            'description': '',
            'type': 'string'},
        'monday': {
            'name': 'monday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every monday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        'tuesday': {
            'name': 'tuesday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every tuesday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        'wednesday': {
            'name': 'wednesday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every wednesday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        'thursday': {
            'name': 'thursday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every thursday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        'friday': {
            'name': 'friday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every friday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        'saturday': {
            'name': 'saturday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every saturday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        'sunday': {
            'name': 'sunday',
            'is_required': false,
            'description': 'Comma-delimited lists of time ranges that are "valid" times for every sunday. Each time range is in the form of HH:MM-HH:MM, where hours are specified on a 24 hour clock. For example, 00:15-24:00 means 12:15am in the morning for this day until 12:00am midnight (a 23 hour, 45 minute total time range). If you wish to exclude an entire day from the timeperiod, simply do not include it in the timeperiod definition.',
            'type': 'string'},
        // [exception] directive not included, impossible to describe with these structures
        'exclude': {
            'name': 'exclude',
            'is_required': false,
            'description': 'Other timeperiod definitions whose time ranges should be excluded from this timeperiod',
            'type': '*timeperiod'},
    };
    
    var command_properties = {
        'command_name': {
            'name': 'command_name',
            'is_required': true,
            'description': 'the short name used to identify the command. It is referenced in contact, host, and service definitions (in notification, check, and event handler directives), among other places.',
            'type': 'shortname'},
        'command_line': {
            'name': 'command_line',
            'is_required': true,
            'description': 'This directive is used to define what is actually executed when the command is used for service or host checks, notifications, or event handlers. Before the command line is executed, all valid macros are replaced with their respective values. Also, if you want to pass a dollar sign ($) on the command line, you have to escape it with another dollar sign.',
            'type': 'string'},
    };
    
    var structure = {
        'host': { 
          'id': 'host',
          'name': 'Host',
          'names': 'Hosts',
          'description': 'Defines a physical server, workstation, device, etc. that resides on your network',
          'key': 'host_name',
          'properties': host_properties,
          'default_columns': ['host_name', 'address']},
        'hostgroup': { 
          'id': 'hostgroup',
          'name': 'Host group',
          'names': 'Host groups',
          'description': 'Groups several hosts in a single entity',
          'key': 'hostgroup_name',
          'properties': hostgroup_properties,
          'default_columns': ['hostgroup_name']},
        'service': { 
          'id': 'service',
          'name': 'Service',
          'names': 'Services',
          'description': 'Identifies a "service" that runs on a host. The term "service" is used very loosely. It can mean an actual service that runs on the host (POP, SMTP, HTTP, etc.) or some other type of metric associated with the host (response to a ping, number of logged in users, free disk space, etc.).',
          'key': 'service_description',
          'properties': service_properties,
          'default_columns': ['service_description', 'host_name', 'hostgroup_name']},
        'servicegroup': { 
          'id': 'servicegroup',
          'name': 'Service group',
          'names': 'Service groups',
          'description': 'A service group definition is used to group one or more services together for simplifying configuration.',
          'key': 'servicegroup_name',
          'properties': servicegroup_properties,
          'default_columns': ['service_description', 'host_name', 'hostgroup_name']},
        'contact': { 
          'id': 'contact',
          'name': 'Contact',
          'names': 'Contacts',
          'description': 'Used to identify someone who should be contacted in the event of a problem on your network',
          'key': 'contact_name',
          'properties': contact_properties,
          'default_columns': ['contact_name', 'email']},
        'contactgroup': { 
          'id': 'contactgroup',
          'name': 'Contact group',
          'names': 'Contact groups',
          'description': 'A contact group definition is used to group one or more contacts together for the purpose of sending out alert/recovery notifications',
          'key': 'contactgroup_name',
          'properties': contactgroup_properties,
          'default_columns': ['contactgroup_name', 'members']},
        'timeperiod': { 
          'id': 'timeperiod',
          'name': 'Time period',
          'names': 'Time periods',
          'description': 'A time period is a list of times during various days that are considered to be "valid" times for notifications and service checks. It consists of time ranges for each day of the week that "rotate" once the week has come to an end. Different types of exceptions to the normal weekly time are supported, including: specific weekdays, days of generic months, days of specific months, and calendar dates.',
          'key': 'timeperiod_name',
          'properties': timeperiod_properties,
          'default_columns': ['timeperiod_name']},
        'command': { 
          'id': 'command',
          'name': 'Command',
          'names': 'Commands',
          'description': 'Defines a console command executed when needed by another component',
          'key': 'command_name',
          'properties': command_properties,
          'default_columns': ['command_name']},
    };

    return structure;
 });