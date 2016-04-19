# -*- coding: utf-8 -*-
"""
/***************************************************************************
 This part of the Midvatten plugin...
(1) updates coordinates from map position or
(2) updates map position from given coordinates 
                             -------------------
        begin                : 2011-10-18
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
import midvatten_utils as utils


class UpdateGeometry(object):
    def __init(self, ):
        """
        :return: None
        """
        pass

    def update_coordinates(self, observations=[]):
        """
        Updates coordinates in table from geometry
        :param observations: List of unicode strings
        :return: None
        """
        observations_string_for_sql = self.create_observation_string(observations)
        sql = u''.join([u"select obsid from obs_points where (Geometry is null or Geometry ='') and obsid in ", observations_string_for_sql])
        is_empty = self.check_not_empty_result(sql, "Coordinates will not be updated because positions (geometries) are missing for")
        if is_empty:
            return

        update_east = u''.join([u"UPDATE OR IGNORE obs_points SET east=X(Geometry) WHERE obsid IN ", observations_string_for_sql])
        update_north = u''.join([u"UPDATE OR IGNORE obs_points SET north=Y(Geometry) WHERE obsid IN ", observations_string_for_sql])
        list_of_sqls = [update_east.encode('utf-8'), update_north.encode('utf-8')]
        utils.sql_alter_db(list_of_sqls)

    def update_position(self, observations=[]):
        """
        Updates geometries from coordinates in table
        :param observations: List of unicode strings
        :return: None
        """
        observations_string_for_sql = self.create_observation_string(observations)
        sql = u''.join([u"select obsid from obs_points where (Geometry is null or Geometry ='') and obsid in ", observations_string_for_sql])
        is_empty = self.check_not_empty_result(sql, "Positions (geometries) will not be updated because coordinates are missing for")
        if is_empty:
            return

        sql = r"""SELECT srid FROM geometry_columns where f_table_name = 'obs_points'"""
        ConnectionOK, result = utils.sql_load_fr_db(sql)
        EPSGID= utils.returnunicode(result[0][0])
        #Then do the operation
        sql = u''.join([u"Update or ignore 'obs_points' SET Geometry=MakePoint(east, north, ", EPSGID, u") WHERE obsid IN ", observations_string_for_sql])
        utils.sql_alter_db(sql.encode('utf-8'))

    @staticmethod
    def create_observation_string(observations=[]):
        ur"""
        Creates a string from a list of observations
        :param observations: A list of observations
        :return: A string surrounded by ( and )

        >>> UpdateGeometry.create_observation_string([u'1', u'2', u'3'])
        u'(1, 2, 3)'
        """
        observations = [utils.returnunicode(obs) for obs in observations]
        observations_string_for_sql = u''.join([u'(', u', '.join(observations), u')'])  #turn list into string
        return observations_string_for_sql

    def check_not_empty_result(self, sql, errormsg):
        """
        Check if sql returns an empty result
        :param sql: An sql string
        :param errormsg: An error msg to print if the result is empty
        :return: 1 if empty or 0 if not empty
        """
        encoded = sql.encode('utf-8')
        connectionOK, result = utils.sql_load_fr_db(encoded)
        if len(result)==0:
            return 1
        else:
            utils.pop_up_info(errormsg + "\n" + result[0][0] + "\n")
            return 0
