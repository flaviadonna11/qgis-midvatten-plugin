# -*- coding: utf-8 -*-
"""
/***************************************************************************
 This part of the Midvatten plugin tests the sectionplot.

 This part is to a big extent based on QSpatialite plugin.
                             -------------------
        begin                : 2016-03-08
        copyright            : (C) 2016 by joskal (HenrikSpa)
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

import utils_for_tests
import midvatten_utils as utils
from utils_for_tests import init_test
from tools.tests.mocks_for_tests import DummyInterface
from nose.tools import raises
from mock import mock_open, patch
from mocks_for_tests import MockUsingReturnValue, MockReturnUsingDict, MockReturnUsingDictIn, MockQgisUtilsIface, MockNotFoundQuestion, MockQgsProjectInstance, DummyInterface2
import mock
import io
import midvatten
import os
from qgis.core import QgsMapLayerRegistry, QgsDataSourceURI, QgsVectorLayer
import qgis
import sectionplot
from PyQt4 import QtCore



class _TestSectionPlot(object):
    """ The test doesn't go through the whole section plot unfortunately
    """
    temp_db_path = u'/tmp/tmp_midvatten_temp_db.sqlite'
    answer_yes_obj = MockUsingReturnValue()
    answer_yes_obj.result = 1
    answer_no_obj = MockUsingReturnValue()
    answer_no_obj.result = 0
    answer_yes = MockUsingReturnValue(answer_yes_obj)
    crs_question = MockUsingReturnValue([3006])
    dbpath_question = MockUsingReturnValue(temp_db_path)
    mocked_iface = MockQgisUtilsIface()  #Used for not getting messageBar errors
    mock_dbpath = MockUsingReturnValue(MockQgsProjectInstance([temp_db_path]))
    mock_askuser = MockReturnUsingDictIn({u'It is a strong': answer_no_obj, u'Please note!\nThere are ': answer_yes_obj}, 1)
    skip_popup = MockUsingReturnValue('')

    @mock.patch('midvatten.utils.askuser', answer_yes.get_v)
    @mock.patch('midvatten_utils.QgsProject.instance', autospec=True)
    @mock.patch('create_db.PyQt4.QtGui.QInputDialog.getInteger')
    @mock.patch('create_db.PyQt4.QtGui.QFileDialog.getSaveFileName')
    def setUp(self, mock_savefilename, mock_crsquestion, mock_qgsproject_instance):
        mock_crsquestion.return_value = [3006]
        mock_savefilename.return_value = TestSectionPlot.temp_db_path

        self.dummy_iface = DummyInterface2()
        self.iface = self.dummy_iface.mock
        self.midvatten = midvatten.midvatten(self.iface)
        try:
            os.remove(TestSectionPlot.temp_db_path)
        except OSError:
            pass
        self.midvatten.new_db()
        self.midvatten.ms.settingsareloaded = True

    def tearDown(self):
        #Delete database
        try:
            os.remove(TestSectionPlot.temp_db_path)
        except OSError:
            pass

    @mock.patch('midvatten_utils.QgsProject.instance', mock_dbpath.get_v)
    def test_plot_section(self):
        """For now, the test only initiates the plot. Check that it does not crash """
        utils.sql_alter_db(u'''insert into obs_lines (obsid, geometry) values ("L1", GeomFromText('LINESTRING(633466.711659 6720684.24498, 633599.530455 6720727.016568)', 3006))''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry) values ("P1", GeomFromText('POINT(633466, 711659)', 3006))''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry) values ("P2", GeomFromText('POINT(6720727, 016568)', 3006))''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry) values ("P3", GeomFromText('POINT(6720728, 016569)', 3006))''')
        uri = QgsDataSourceURI()
        uri.setDatabase(TestSectionPlot.temp_db_path)
        uri.setDataSource('', 'obs_lines', 'geometry', '', 'obsid')

        self.vlayer = QgsVectorLayer(uri.uri(), 'TestLayer', 'spatialite')
        features = self.vlayer.getFeatures()
        for feature in features:
            featureid = feature.id()

        self.vlayer.setSelectedFeatures([featureid])

        @mock.patch('midvatten.utils.getselectedobjectnames', autospec=True)
        @mock.patch('midvatten.qgis.utils.iface', autospec=True)
        def _test_plot_section(self, mock_iface, mock_getselectedobjectnames):
            mock_iface.mapCanvas.return_value.currentLayer.return_value = self.vlayer
            mock_getselectedobjectnames.return_value = (u'P1', u'P2', u'P3')
            mock_mapcanvas = mock_iface.mapCanvas.return_value
            mock_mapcanvas.layerCount.return_value = 0
            self.midvatten.plot_section()
            self.myplot = self.midvatten.myplot
            self.myplot.drillstoplineEdit.setText(u"%berg%")
            self.myplot.draw_plot()
            self.selected_obsids = self.myplot.selected_obsids
        _test_plot_section(self)

        assert self.myplot.drillstoplineEdit.text() == u'%berg%'
        assert utils_for_tests.create_test_string(self.myplot.selected_obsids) == "['P1' 'P2' 'P3']"

    @mock.patch('midvatten_utils.QgsProject.instance', mock_dbpath.get_v)
    def test_plot_section_with_depth(self):
        utils.sql_alter_db(u'''insert into obs_lines (obsid, geometry) values ("L1", GeomFromText('LINESTRING(633466.711659 6720684.24498, 633599.530455 6720727.016568)', 3006))''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry, length) values ("P1", GeomFromText('POINT(633466, 711659)', 3006), 2)''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry, length) values ("P2", GeomFromText('POINT(6720727, 016568)', 3006), "1")''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry, length) values ("P3", GeomFromText('POINT(6720727, 016568)', 3006), NULL)''')

        uri = QgsDataSourceURI()
        uri.setDatabase(TestSectionPlot.temp_db_path)
        uri.setDataSource('', 'obs_lines', 'geometry', '', 'obsid')

        self.vlayer = QgsVectorLayer(uri.uri(), 'TestLayer', 'spatialite')
        features = self.vlayer.getFeatures()
        for feature in features:
            featureid = feature.id()

        self.vlayer.setSelectedFeatures([featureid])

        @mock.patch('midvatten.utils.getselectedobjectnames', autospec=True)
        @mock.patch('midvatten.qgis.utils.iface', autospec=True)
        def _test_plot_section_with_depth(self, mock_iface, mock_getselectedobjectnames):
            mock_iface.mapCanvas.return_value.currentLayer.return_value = self.vlayer
            mock_getselectedobjectnames.return_value = (u'P1', u'P2', u'P3')
            mock_mapcanvas = mock_iface.mapCanvas.return_value
            mock_mapcanvas.layerCount.return_value = 0
            self.midvatten.plot_section()
        _test_plot_section_with_depth(self)

    @mock.patch('midvatten_utils.QgsProject.instance', mock_dbpath.get_v)
    def test_plot_section_with_w_levels(self):
        utils.sql_alter_db(u'''insert into obs_lines (obsid, geometry) values ("L1", GeomFromText('LINESTRING(633466.711659 6720684.24498, 633599.530455 6720727.016568)', 3006))''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry, length) values ("P1", GeomFromText('POINT(633466, 711659)', 3006), 2)''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry, length) values ("P2", GeomFromText('POINT(6720727, 016568)', 3006), "1")''')
        utils.sql_alter_db(u'''insert into obs_points (obsid, geometry, length) values ("P3", GeomFromText('POINT(6720727, 016568)', 3006), NULL)''')
        utils.sql_alter_db(u'''insert into w_levels (obsid, date_time, meas, h_toc, level_masl) values ("P1", "2015-01-01 00:00:00", "15", "200", "185")''')
        utils.sql_alter_db(u'''insert into w_levels (obsid, date_time, meas, h_toc, level_masl) values ("P2", "2015-01-01 00:00:00", "17", "200", "183")''')

        uri = QgsDataSourceURI()
        uri.setDatabase(TestSectionPlot.temp_db_path)
        uri.setDataSource('', 'obs_lines', 'geometry', '', 'obsid')

        self.vlayer = QgsVectorLayer(uri.uri(), 'TestLayer', 'spatialite')
        features = self.vlayer.getFeatures()
        for feature in features:
            featureid = feature.id()

        self.vlayer.setSelectedFeatures([featureid])

        @mock.patch('midvatten.utils.getselectedobjectnames', autospec=True)
        @mock.patch('midvatten.qgis.utils.iface', autospec=True)
        def _test_plot_section_with_depth(self, mock_iface, mock_getselectedobjectnames):
            mock_iface.mapCanvas.return_value.currentLayer.return_value = self.vlayer
            mock_getselectedobjectnames.return_value = (u'P1', u'P2', u'P3')
            mock_mapcanvas = mock_iface.mapCanvas.return_value
            mock_mapcanvas.layerCount.return_value = 0
            self.midvatten.plot_section()
        _test_plot_section_with_depth(self)
