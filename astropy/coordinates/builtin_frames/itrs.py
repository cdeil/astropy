# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from ..representation import CartesianRepresentation
from ..baseframe import BaseCoordinateFrame, TimeFrameAttribute
from .utils import DEFAULT_OBSTIME


class ITRS(BaseCoordinateFrame):
    """
    A coordinate or frame in the Intertaional Terrestrial Reference System
    (ITRS).  This is approximately a geocentric system, although strictly it is
    defined by a series of reference locations near the surface of the Earth.
    """

    default_representation = CartesianRepresentation

    obstime = TimeFrameAttribute(default=DEFAULT_OBSTIME)
