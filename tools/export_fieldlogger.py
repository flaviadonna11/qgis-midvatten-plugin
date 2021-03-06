# -*- coding: utf-8 -*-
"""
/***************************************************************************
 This is the part of the Midvatten plugin that enables quick export of data from the database
                              -------------------
        begin                : 2015-08-30
        copyright            : (C) 2011 by joskal
        email                : groundwatergis [at] gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import PyQt4
import os
import os.path
import qgis.utils
from collections import OrderedDict

import midvatten_utils as utils
from definitions.midvatten_defs import standard_parameters_for_wquality, standard_parameters_for_wflow, standard_parameters_for_wsample
from import_data_to_db import midv_data_importer

export_fieldlogger_ui_dialog =  PyQt4.uic.loadUiType(os.path.join(os.path.dirname(__file__),'..','ui', 'export_fieldlogger_ui_dialog.ui'))[0]


class ExportToFieldLogger(PyQt4.QtGui.QMainWindow, export_fieldlogger_ui_dialog):
    """ Class handling export of data for fieldlogger """
    
    def __init__(self, parent, settingsdict1={}, obsids=None):
        self.iface = parent
        self.obsids = obsids

        self.settingsdict = settingsdict1
        PyQt4.QtGui.QDialog.__init__(self, parent)
        self.setAttribute(PyQt4.QtCore.Qt.WA_DeleteOnClose)
        self.setupUi(self)  # Required by Qt4 to initialize the UI
        self.setWindowTitle("Export to FieldLogger") # Set the title for the dialog

        self.parameters = self.create_parameters()
        self.unhidden_types_parameters = self.get_unhidden_types_parameters_names(self.parameters)
        self.set_headers(self.gridLayout_selections, self.unhidden_types_parameters, self.gridWidget_selections)
        self.set_and_connect_select_from_map(self.gridLayout_selections, self.unhidden_types_parameters, self.gridWidget_selections)
        self.set_and_connect_selectall(self.gridLayout_selections, self.unhidden_types_parameters, self.gridWidget_selections)
        self.add_line(self.gridLayout_selections, len(self.unhidden_types_parameters), self.gridWidget_selections)
        self.obsids = utils.get_all_obsids()

        self.selection_dict = self.build_selection_dict(self.obsids, self.unhidden_types_parameters, self.gridWidget_selections)
        self.set_obsids_and_parameters_checkboxes(self.gridLayout_selections, self.selection_dict, self.unhidden_types_parameters)

        self.connect(self.pushButtonExport, PyQt4.QtCore.SIGNAL("clicked()"), self.export_selected)
        self.connect(self.pushButtonImportWellsfile, PyQt4.QtCore.SIGNAL("clicked()"), self.select_from_wells)

        self.show()

    def create_parameters(self):
        """ Creaters self.parameters dict with parameters
        :return: a dict like "{'typename': {'parameter': Parameter()}}"
        """
        types = {}

        types_tuples = [(u'level', ((u'meas', (u'm',)),)),
                        (u'flow', standard_parameters_for_wflow()),
                        (u'quality', standard_parameters_for_wquality()),
                        (u'sample', standard_parameters_for_wsample())]

        for parameter_type, parameters_units_tuple in types_tuples:
            types[parameter_type] = OrderedDict()
            types[parameter_type].update(self.create_parameters_from_tuple(parameter_type, parameters_units_tuple))
            types[parameter_type][u'comment'] = Parameter(u'comment', u'make comment...', parameter_type, u'', u'text', True)

        return types

    def create_parameters_from_tuple(self, parameter_type, parameters_units_tuple):
        parameters = OrderedDict()
        for param, units in parameters_units_tuple:
            for unit in units:
                if len(units) > 1:
                    paramname = u'.'.join((param, unit))
                else:
                    paramname = param
                hint = unit
                parameters[paramname] = Parameter(paramname, hint, parameter_type, unit)
        return parameters

    def get_unhidden_types_parameters_names(self, parameters):
        unhidden_parameternames = tuple([(typename, parametername) for typename, parameter_dict in sorted(parameters.iteritems())
                                   for parametername, parameter in sorted(parameter_dict.iteritems()) if not parameter.hidden])
        return unhidden_parameternames

    def set_headers(self, grid, unhidden_types_parameters, widget_parent):
        """
        Creates Qlabel headers for all parameters
        :param grid: A QGridLayout.
        :param unhidden_types_parameters: A dict with type as key an innerdict with parameters as value
        :return: None
        """
        rownr = grid.rowCount()

        for colnr, type_parameter in enumerate(unhidden_types_parameters):
            label = PyQt4.QtGui.QLabel('.'.join(type_parameter))
            grid.addWidget(label, rownr, colnr + 1)

    def set_and_connect_select_from_map(self, grid, unhidden_types_parameters, widget_parent):
        """
        Creates buttons that selects all parameters for selected obsids in obs_points
        :param grid: A QGridLayout.
        :param unhidden_types_parameters: A dict with type as key an innerdict with parameters as value
        :param widget_parent:
        :return:
        """
        rownr = grid.rowCount()
        grid.addWidget(PyQt4.QtGui.QLabel('Select from map selection'), rownr, 0)
        for colnr, type_parameter in enumerate(unhidden_types_parameters):
            pushbutton = PyQt4.QtGui.QPushButton('Select from map', widget_parent)
            pushbutton.setToolTip('Select ' + '.'.join(type_parameter) + ' for all obsids selected in map')
            pushbutton.setObjectName('.'.join(type_parameter))
            grid.addWidget(pushbutton, rownr, colnr + 1)
            self.connect(pushbutton, PyQt4.QtCore.SIGNAL("clicked()"), self.select_from_map_click)

    def select_from_map_click(self):
        """
        Method representing a select_from_map click.

        self.sender() is used to find the currently clicked checkbox.
        :return: None
        """
        PyQt4.QtGui.QApplication.setOverrideCursor(PyQt4.QtGui.QCursor(PyQt4.QtCore.Qt.WaitCursor))  #show the user this may take a long time...
        pushbutton = self.sender()
        type_parameter_name = pushbutton.objectName()
        self.select_from_map(type_parameter_name)
        PyQt4.QtGui.QApplication.restoreOverrideCursor()

    def select_from_map(self, type_parameter_name):
        """
        Selects parameter for all obsids selected in map
        :param type_parameter_name: A parametername like type.parameter
        :return: None
        """
        selected_obsids = utils.get_selected_features_as_tuple('obs_points')
        for obsid in selected_obsids:
            types_dict = self.selection_dict[obsid]
            splitted = type_parameter_name.split('.')
            typename = splitted[0]
            parametername = '.'.join(splitted[1:])
            checkbox = types_dict[typename][parametername]
            checkbox.setChecked(True)

    def set_and_connect_selectall(self, grid, unhidden_types_parameters, widget_parent):
        """
        Creates checkboxes for select all for all parameters
        :param grid: A QGridLayout.
        :param unhidden_types_parameters: A dict with type as key an innerdict with parameters as value
        :return: None
        """
        rownr = grid.rowCount()
        grid.addWidget(PyQt4.QtGui.QLabel('Select all'), rownr, 0)

        for colnr, type_parameter in enumerate(unhidden_types_parameters):
            checkbox = PyQt4.QtGui.QCheckBox(widget_parent)
            checkbox.setToolTip('.'.join(type_parameter))
            checkbox.setObjectName('.'.join(type_parameter))
            grid.addWidget(checkbox, rownr, colnr + 1)
            self.connect(checkbox, PyQt4.QtCore.SIGNAL("clicked()"), self.select_all_click)

    def add_line(self, grid, num_cols, widget_parent):
        rownr = grid.rowCount()
        frame = PyQt4.QtGui.QFrame(widget_parent)
        frame.setFrameShape(PyQt4.QtGui.QFrame.HLine)
        grid.addWidget(frame, rownr, 0, 1, num_cols + 1)

    def build_selection_dict(self, obsids, unhidden_types_parameters, parent_widget):
        """ Creates a dict of obsids and their parameter checkbox objects
        :param obsids: A list of obsids
        :param unhidden_types_parameters: A dict with type as key an innerdict with parameters as value
        :param parent_widget: The parent widget. It might be needed for this to work, but not sure.
        :return: a dict like {'obsid': {'parametername': QCheckBox, ...}, ...}
        """
        selection_dict = {}
        for obsid in obsids:
            type_dict = {}
            for typename, parametername in unhidden_types_parameters:
                checkbox = PyQt4.QtGui.QCheckBox(parent_widget)
                type_dict.setdefault(typename, {})[parametername] = checkbox
            selection_dict[obsid] = type_dict
        return selection_dict

    def set_obsids_and_parameters_checkboxes(self, grid, selection_dict, unhidden_types_parameters):
        """
        Creates a matrix of checkboxes for choosing parameters
        :param grid: A QGridLayout.
        :param selection_dict: a dict like {'obsid': {'parametername': QCheckBox, ...}, ...}
        :return: None
        """
        start_rownr = grid.rowCount()
        for rownr, obs_types_dict_tuple in enumerate(sorted(selection_dict.iteritems())):
            obsid, types_dict = obs_types_dict_tuple
            grid.addWidget(PyQt4.QtGui.QLabel(obsid), rownr + start_rownr, 0)

            for colnr, type_parameter in enumerate(unhidden_types_parameters):
                typename, parametername = type_parameter
                checkbox = types_dict[typename][parametername]
                checkbox.setMinimumSize(20, 20)
                checkbox.setToolTip('.'.join((obsid, typename, parametername)))
                grid.addWidget(checkbox, rownr + start_rownr, colnr + 1)

    def select_all_click(self):
        """
        Method representing a select_all click.

        self.sender() is used to find the currently clicked checkbox.
        :return: None
        """
        PyQt4.QtGui.QApplication.setOverrideCursor(PyQt4.QtGui.QCursor(PyQt4.QtCore.Qt.WaitCursor))  #show the user this may take a long time...
        checkbox = self.sender()
        type_parameter_name = checkbox.objectName()
        check_state = checkbox.isChecked()
        self.select_all(type_parameter_name, check_state)
        PyQt4.QtGui.QApplication.restoreOverrideCursor()

    def select_all(self, type_parameter_name, check_state):
        """
        Selects or deselects a parameter for all obsids
        :param type_parameter_name: A parametername like type.parameter
        :param check_state: The state of the currently selected select_all checkbox.
        :return:
        """
        for obsid, types_dict in self.selection_dict.iteritems():
            splitted = type_parameter_name.split(u'.')
            typename = splitted[0]
            parametername = '.'.join(splitted[1:])
            checkbox = types_dict[typename][parametername]
            checkbox.setChecked(check_state)

    def select_from_wells(self):
        """ Select all from imported wells-file
        :return:
        """
        selection_dict = self.selection_dict

        importinstance = midv_data_importer()
        obsid_dict = importinstance.parse_wells_file()
        if obsid_dict == u'cancel':
            qgis.utils.iface.messageBar().pushMessage("Select from wells file: No file was chosen or no rows could be parsed.")
            return u'cancel'

        failed_imports = []
        for obsid, types_dict in obsid_dict.iteritems():
            for typename, parameters in types_dict.iteritems():
                for parameter, unit in parameters:
                    try:
                        types_dict = selection_dict[obsid]
                    except KeyError:
                        failed_imports.append([obsid, typename, parameter, unit])
                        continue
                    try:
                        parameters =  types_dict[typename]
                    except KeyError:
                        failed_imports.append([obsid, typename, parameter, unit])
                        continue
                    try:
                        checkbox = parameters[u'.'.join([parameter, unit])]
                    except KeyError:
                        try:
                            checkbox = parameters[parameter]
                        except KeyError:
                            failed_imports.append([obsid, typename, parameter, unit])
                            continue
                    checkbox.setChecked(True)
        if obsid_dict:
            utils.pop_up_info('Failed to import parameters:\n' + '\n'.join([', '.join(x) for x in failed_imports if x[2] != u'comment']))

    def export_selected(self):
        """ Export the selected obsids and parameters to a file
        """
        self.write_printlist_to_file(self.create_export_printlist())

    def create_export_printlist(self):
        """
        Creates a result list with FieldLogger format from selected obsids and parameters
        :return: a list with result lines to export to file
        """
        selection_dict = self.selection_dict
        types_parameters_dict = self.parameters

        latlons = utils.get_latlon_for_all_obsids()

        chosen_parameter_headers = set()

        obsid_rows = []
        for obsid, types_dict in selection_dict.iteritems():
            for typename, parameter_dict in types_dict.iteritems():
                subname = None
                chosen_parameters = set()
                for parameter, checkbox in parameter_dict.iteritems():
                    if checkbox.isChecked():
                        subname = '.'.join((obsid, typename))

                        chosen_parameters.add(types_parameters_dict[typename][parameter].full_name)
                        chosen_parameters.update([v.full_name for k, v in types_parameters_dict[typename].iteritems() if v.hidden])

                        chosen_parameter_headers.add((typename, parameter))
                        chosen_parameter_headers.update([(typename, k) for k, v in types_parameters_dict[typename].iteritems() if v.hidden])

                if subname is not None:
                    lat, lon = latlons.get(obsid)
                    obsid_rows.append(';'.join((obsid, subname, str(lat), str(lon), '|'.join(chosen_parameters))))


        #Sort the parameters to the same order as they were entered into the ordered types dict.
        sorted_chosen_parameter_headers = [parameter.get_header_word() for typename, parameters in sorted(types_parameters_dict.iteritems()) for parametername, parameter in parameters.iteritems() if (typename, parametername) in chosen_parameter_headers]

        printlist = []
        printlist.append(u"FileVersion 1;" + str(len(sorted_chosen_parameter_headers)))
        printlist.append(u"NAME;INPUTTYPE;HINT")
        printlist.extend(sorted_chosen_parameter_headers)
        printlist.append(u'NAME;SUBNAME;LAT;LON;INPUTFIELD')

        printlist.extend(sorted(obsid_rows))
        return printlist

    def write_printlist_to_file(self, printlist):
        filename = PyQt4.QtGui.QFileDialog.getSaveFileName(None, 'Choose a file name', '', 'csv (*.csv)')

        if not filename:
            return
        try:
            with open(filename, 'w') as f:
                f.write(u'\n'.join(printlist).encode('utf-8'))
        except IOError, e:
            utils.pop_up_info("Writing of file failed!: " + str(e))
        except UnicodeDecodeError, e:
            utils.pop_up_info("Error writing " + str(printlist))


class Parameter(object):
    def __init__(self, name, hint, parameter_type, unit='', valuetype='numberDecimal|numberSigned', hidden=False):
        """ A class representing a parameter

        :param name: The name of the parameter
        :param hint: A hint to the user
        :param parameter_type: ex: flow, level, quality
        :param valuetype: a valuetype, ex: 'text', 'numberDecimal', 'numberSigned'
        :param hidden: True/False. If True, the parameter will not be printed as a checkbox.
        :return: None
        """
        self.name = name
        self.unit = unit
        self.parameter_type = parameter_type
        self.valuetype = valuetype
        self.hidden = hidden
        self.header_word = None

        if not hint:
            self.hint = self.name
        else:
            self.hint = utils.returnunicode(hint)

        if self.name.endswith(self.unit):
            self.full_name = '.'.join((self.parameter_type[0], self.name))
        else:
            self.full_name = '.'.join((self.parameter_type[0], self.name, self.unit))

    def __repr__(self):
        return self.name

    def get_header_word(self):
        if self.header_word is None:
            self.header_word = ';'.join((self.full_name, self.valuetype, self.hint))
        return self.header_word


