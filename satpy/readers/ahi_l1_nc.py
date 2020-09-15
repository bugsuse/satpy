#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Satpy developers
#
# This file is part of satpy.
#
# satpy is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# satpy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# satpy.  If not, see <http://www.gnu.org/licenses/>.
"""Advanced Himawari Imager (AHI) standard format data reader.

References:
    - Himawari-8/9 Himawari L1 Gridded Data User's Guide
    - http://www.data.jma.go.jp/mscweb/en/himawari89/space_segment/spsg_ahi.html

Time Information
****************

AHI observations use the idea of a "scheduled" time and an "observation time.
The "scheduled" time is when the instrument was told to record the data,
usually at a specific and consistent interval. The "observation" time is when
the data was actually observed. Scheduled time can be accessed from the
`scheduled_time` metadata key and observation time from the `start_time` key.

"""

import logging

import xarray as xr
import dask.array as da
from pyresample import geometry
from satpy.readers.netcdf_utils import NetCDF4FileHandler, netCDF4

logger = logging.getLogger(__name__)


class AHIL1FileHandler(NetCDF4FileHandler):
    def __init__(self, filename, filename_info, filetype_info):
        self.filename = filename
        self.nc = xr.open_dataset(filename)
        self.filename_info = filename_info
        self.filetype_info = filetype_info
        self.ncols = self.filename_info.get('pixel_number')
        self.nlines = self.filename_info.get('line_number')
        self.metadata = {}

    @property
    def start_time(self):
        """Get start time."""
        return self.nc['start_time'].values[0]

    @property
    def end_time(self):
        """Get end time."""
        return self.nc['end_time'].values[0]

    @property
    def platform_shortname(self):
        """Get platform shortname."""
        return self.filename_info['platform_shortname']

    @property
    def sensor(self):
        """Get sensor."""
        return "ahi"

    @property
    def sensor_names(self):
        """Get sensor set."""
        return {self.sensor}

    def get_dataset(self, dsid, ds_info):
        """Get dataset."""
        logger.debug(f"Getting data for: {dsid['name']}")
        scale_factor = ds_info.get('scale_factor', 1)
        offset = ds_info.get('add_offset', 0)
        data = self.nc[dsid['name']]

        if data.ndim >= 2:
            data = data * scale_factor + offset

            return data.rename({'latitude':'y', 'longitude':'x'})
        else:
            return data

    def get_area_def(self, dsid):
        """Get the area definition.

        This is fixed, but not defined in the file. So we must
        generate it ourselves with some assumptions."""

        _lon, _lat = self.nc['longitude'].values, self.nc['latitude'].values
        area_extent = [_lon.min(), _lat.min(), _lon.max(), _lat.max()]

        proj_param = 'EPSG:4326'

        area = geometry.AreaDefinition('gridded_himawari',
                                       'A gridded Himawari area',
                                       'longlat',
                                       proj_param,
                                       self.ncols,
                                       self.nlines,
                                       area_extent)
        self.area = area

        return area

    def get_metadata(self, data, ds_info):
         """Get metadata."""
         metadata = {}
         metadata.update(data.attrs)
         metadata.update(ds_info)
         metadata.update({
             'platform_shortname': self.platform_shortname,
             'sensor': self.sensor,
             'start_time': self.start_time,
             'end_time': self.end_time,
         })

         return metadata

