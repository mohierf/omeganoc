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
define(['jquery', 'config.data', 'select2', 'jquery.validate'], function(jQuery, structure) {
    jQuery(function() {
        var data = _conf_details_data;
        var type = _conf_details_type;
        var type_data = structure[type];

        // Set up validation
        for(i in type_data.properties) {
            // Does a field exist for this property ?
            var field = jQuery('#' + i);
            if(field.length > 0) {
                // Yes !
                var fieldtype = type_data.properties[i].type;
                //var multiple = false;
                if(fieldtype.indexOf('*') == 0) {
                    //multiple = true;
                    fieldtype = fieldtype.substr(1); // Remove the leading *
                }

                // Basic types
                switch(fieldtype) {
                case 'integer':
                    // For now all integers should be zero or positive
                    field.attr('min', '0');
                    break;
                case 'shortname':
                    field.attr('required', 'required');
                    field.attr('pattern', '^[^`~!$%^&*"|\'<>?,()=]+$');
                    field.attr('placeholder', 'Unspecified name');
                    break;
                case 'string':
                    field.attr('placeholder', 'Unspecified text');
                    break;
                case 'url':
                    field.attr('placeholder', 'Unspecified URL');
                    break;
                case 'email':
                    field.attr('placeholder', 'Unspecified email');
                    break;
                case 'address':
                    field.attr('placeholder', 'Unspecified address');
                    break;
                }
            }
        }

        // Activate validation
        jQuery('form.details-form').validate();

        // Select2 lists
        jQuery('select[multiple]').select2({
            width: '400px',
            placeholder: 'Empty list',
        });

        // Open / collapse fieldsets
        jQuery('form > fieldset > legend').click(function() {
            jQuery(this).parent().toggleClass('collapsed');
        });
    });
});
