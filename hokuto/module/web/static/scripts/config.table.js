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
define(['jquery', 'config.data', 'onoc.createurl', 'console', 'datatables', 'jquery.hashchange'], function(jQuery, structure, createurl, Console) {
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
    
    function _applyCurrentHash() {
        _applyHash(window.location.hash.substr(1));
    }
    
    function _applyHash(hash) {
        if(!hash) {
            Console.warn('Could not apply an empty hash !');
            return;
        }
        
        // Remove the trailing s if it's there
        if(hash.charAt(hash.length - 1) == 's')
            hash = hash.substr(0, hash.length - 1);
        
        var typeName = hash;
        var isTemplate = false;
        
        // If that a template ?
        if(typeName.match('template')) {
            // Yup
            isTemplate = true;
            typeName = typeName.substr(0, typeName.length - 8);
        }
        
        var targetStruct = structure[typeName];
        
        if(!targetStruct) {
            Console.warn('Could not find a structure type for type "' + typeName + '"');
            return;
        }
        
        Console.log('Going to ' + targetStruct.name);

        var serviceUrl = createurl('/config/list/' + targetStruct.id + (isTemplate ? 'templates' : 's'));
        var table = jQuery('#config_main_list');
        
        var columns = [];
        for(var col in targetStruct.default_columns) {
            var colName = targetStruct.default_columns[col];
            
            // If we have a template then the "primary key" changes
            if(isTemplate && colName == targetStruct.key)
                colName = 'name';
            
            columns.push({'title': colName, 
                          'data': colName,
                          'defaultContent':''});
        }
        columns.push({ 'title': 'Edit',
                       'data': targetStruct.key,
                       'render': function(data, type, row, meta) {
                           return '<a href="' + createurl('/config/' + typeName + (isTemplate ? 'template/' : '/') + data) + '" class="button">Edit</a>';
                       },
                       'orderable': false,
                       'searchable': false});
        
        if(jQuery.fn.DataTable.isDataTable(table)) {
            // Table already initialized
            // We completely clear it to re-create it later
            // since DataTables does not allow creating / removing 
            // columns on the fly
            table.DataTable().destroy();
            table.empty();
        }
        
        table.dataTable({
            'ajax': serviceUrl,
            'columns': columns,
        });
    }
    
    jQuery(function() {
        
        jQuery(window).hashchange(function() {
            _applyCurrentHash();
        });
        
        var h = window.location.hash;
        if(!h) {
            // If no url hash provided, go to the hosts by default
            _applyHash('hosts');
        }
        else {
            _applyCurrentHash();
        }
    });
});