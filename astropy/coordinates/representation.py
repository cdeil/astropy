# In this file, we define the coordinate representation classes, which are
# used to represent low-level cartesian, spherical, cylindrical, and other #
# coordinate. All classes should define a to_cartesian method and a
# from_cartesian class method. By default, transformations are done via the
# cartesian system, but classes that want to define a smarter transformation
# path can overload the ``represent_as`` method.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import abc

import numpy as np
import astropy.units as u

from .angles import Angle, Longitude, Latitude
from .distances import Distance
from ..extern import six

# Suggestions to improve API
#
# - change PhysicistSphericalRepresentation to PhysicsSphericalRepresentation
# (implemented below).
#
# - add a rotated() method that can rotate the 3D coordinates

__all__ = ["CartesianRepresentation", "SphericalRepresentation",
           "UnitSphericalRepresentation", "PhysicsSphericalRepresentation",
           "CylindricalRepresentation"]


def broadcast_quantity(*args, **kwargs):
    """
    A Quantity-aware version of np.broadcast_arrays
    """
    new_arrays = np.broadcast_arrays(*args)
    new_quantities = []
    for i in range(len(new_arrays)):
        new_quantities.append(args[i].__class__(new_arrays[i], unit=args[i].unit, **kwargs))
    return tuple(new_quantities)


@six.add_metaclass(abc.ABCMeta)
class BaseRepresentation(object):
    """
    Base Representation object, for representing a point in a 3D coordinate system
    """

    def represent_as(self, other_class):
        if other_class == self.__class__:
            return self
        else:
            # The default is to convert via cartesian coordinates
            return other_class.from_cartesian(self.to_cartesian())

    @classmethod
    def from_representation(cls, representation):
        return representation.represent_as(cls)

    # Should be replaced by abstractclassmethod once we support only Python 3
    @abc.abstractmethod
    def from_cartesian(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def to_cartesian(self):
        raise NotImplementedError()


class CartesianRepresentation(BaseRepresentation):
    """
    Representation of points in 3D cartesian coordinates.

    Parameters
    ----------
    x, y, z : `~astropy.units.Quantity` or float or `~numpy.ndarray`
        The x, y, and z coordinates of the point(s), which should either be
        `~astropy.units.Quantity` instances, or can be passed as
        float or `numpy.ndarray` provided that the ``unit`` parameter is
        specified. If ``x``, ``y``, and ``z`` have different shapes, they
        should be broadcastable.

    unit : `~astropy.units.Unit`, optional
        If ``x``, ``y``, or ``z`` are specified as float or
        ``numpy.ndarray``, then ``unit`` should be specified to indicate the
        units for these parameters. If ``x``, ``y``, or ``z`` are
        `~astropy.units.Quantity` instances, and ``unit`` is specified, they
        are converted to ``unit``.

    copy : bool, optional
        If True arrays will be copied rather than referenced.
    """

    def __init__(self, x, y=None, z=None, unit=None, copy=True):

        if y is None and z is None:
            x, y, z = x
        elif (y is None and z is not None) or (y is not None and z is None):
            raise ValueError("x, y, and z are required to instantiate CartesianRepresentation")

        if unit is not None:
            unit = u.Unit(unit)

        x = u.Quantity(x, unit=unit, copy=copy)
        y = u.Quantity(y, unit=unit, copy=copy)
        z = u.Quantity(z, unit=unit, copy=copy)

        if not (x.unit.physical_type == y.unit.physical_type == z.unit.physical_type):
            raise u.UnitsError("x, y, and z should have matching physical types")

        try:
            x, y, z = broadcast_quantity(x, y, z, copy=copy)
        except ValueError:
            raise ValueError("Input parameters x, y, and z cannot be broadcast")

        self._x = x
        self._y = y
        self._z = z

    @property
    def x(self):
        """
        The x componen of the point(s).
        """
        return self._x

    @property
    def y(self):
        """
        The y position of the point(s).
        """
        return self._y

    @property
    def z(self):
        """
        The z position of the point(s).
        """
        return self._z

    @property
    def xyz(self):
        return u.Quantity((self._x, self._y, self._z))

    @classmethod
    def from_cartesian(cls, other):
        return other

    def to_cartesian(self):
        return self


class SphericalRepresentation(BaseRepresentation):
    """
    Representation of points in 3D spherical coordinates.

    Parameters
    ----------
    lon, lat : `~astropy.units.Quantity` or str
        The longitude and latitude of the point(s). The input values are
        passed to the `~astropy.coordinates.Longitude` and
        `~astropy.coordinates.Latitude` class respectively, so any valid
        input for these classes is acceptable. This includes
        `~astropy.units.Quantity` instances, strings, lists of strings, and
        so on. `~astropy.coordinates.Longitude` instances can only be passed
        to ``lon``, and `~astropy.coordinates.Latitude` instances can only be
        passed to ``lat``.

    distance : `~astropy.units.Quantity`
        The distance to the point(s). If the distance is a length, it is
        passed to the :class:`~astropy.coordinates.Distance` class, otherwise
        it is passed to the :class:`~astropy.units.Quantity` class.

    copy : bool, optional
        If True arrays will be copied rather than referenced.
    """

    def __init__(self, lon, lat, distance, copy=True):

        # Let the Longitude and Latitude classes deal with e.g. parsing
        lon = Longitude(lon, copy=copy)
        lat = Latitude(lat, copy=copy)

        if isinstance(distance, u.Quantity) and distance.unit.physical_type == 'length':
            distance = Distance(distance, copy=copy)
        else:
            distance = u.Quantity(distance, copy=copy)

        try:
            lon, lat, distance = broadcast_quantity(lon, lat, distance, copy=copy)
        except ValueError:
            raise ValueError("Input parameters lon, lat, and distance cannot be broadcast")

        self._lon = lon
        self._lat = lat
        self._distance = distance

    @property
    def lon(self):
        """
        The longitude of the point(s).
        """
        return self._lon

    @property
    def lat(self):
        """
        The latitude of the point(s).
        """
        return self._lat

    @property
    def distance(self):
        """
        The distance from the origin to the point(s).
        """
        return self._distance

    def represent_as(self, other_class):
        # Take a short cut if the other clsss is a spherical representation
        if other_class is PhysicsSphericalRepresentation:
            return PhysicsSphericalRepresentation(phi=self.lon,
                                                  theta=90 * u.deg - self.lat,
                                                  distance=self.distance)
        else:
            return super(SphericalRepresentation, self).represent_as(other_class)

    def to_cartesian(self):
        """
        Converts spherical polar coordinates to 3D rectangular cartesian
        coordinates.
        """

        # We need to convert Distance to Quantity to allow negative values.
        if isinstance(self.distance, Distance):
            d = self.distance.view(u.Quantity)
        else:
            d = self.distance

        x = d * np.cos(self.lat) * np.cos(self.lon)
        y = d * np.cos(self.lat) * np.sin(self.lon)
        z = d * np.sin(self.lat)

        return CartesianRepresentation(x=x, y=y, z=z)

    @classmethod
    def from_cartesian(cls, cart):
        """
        Converts 3D rectangular cartesian coordinates to spherical polar
        coordinates.
        """

        xsq = cart.x ** 2
        ysq = cart.y ** 2
        zsq = cart.z ** 2

        r = (xsq + ysq + zsq) ** 0.5
        s = (xsq + ysq) ** 0.5

        lon = np.arctan2(cart.y, cart.x)
        lat = np.arctan2(cart.z, s)

        return SphericalRepresentation(lon=lon, lat=lat, distance=r)


class UnitSphericalRepresentation(BaseRepresentation):
    """
    Representation of points on a unit sphere

    Parameters
    ----------
    lon, lat : `~astropy.units.Quantity` or str
        The longitude and latitude of the point(s). The input values are
        passed to the `~astropy.coordinates.Longitude` and
        `~astropy.coordinates.Latitude` class respectively, so any valid
        input for these classes is acceptable. This includes
        `~astropy.units.Quantity` instances, strings, lists of strings, and
        so on. `~astropy.coordinates.Longitude` instances can only be passed
        to ``lon``, and `~astropy.coordinates.Latitude` instances can only be
        passed to ``lat``.

    copy : bool, optional
        If True arrays will be copied rather than referenced.
    """

    def __init__(self, lon, lat, copy=True):

        # Let the Longitude and Latitude classes deal with e.g. parsing
        lon = Longitude(lon, copy=copy)
        lat = Latitude(lat, copy=copy)

        try:
            lon, lat = broadcast_quantity(lon, lat, copy=copy)
        except ValueError:
            raise ValueError("Input parameters lon and lat cannot be broadcast")

        self._lon = lon
        self._lat = lat

    @property
    def lon(self):
        """
        The longitude of the point(s).
        """
        return self._lon

    @property
    def lat(self):
        """
        The latitude of the point(s).
        """
        return self._lat

    # TODO: implement represent_as for efficient transformations

    def to_cartesian(self):
        """
        Converts spherical polar coordinates to 3D rectangular cartesian
        coordinates.
        """

        x = u.one * np.cos(self.lat) * np.cos(self.lon)
        y = u.one * np.cos(self.lat) * np.sin(self.lon)
        z = u.one * np.sin(self.lat)

        return CartesianRepresentation(x=x, y=y, z=z)

    @classmethod
    def from_cartesian(cls, cart):
        """
        Converts 3D rectangular cartesian coordinates to spherical polar
        coordinates.
        """

        xsq = cart.x ** 2
        ysq = cart.y ** 2
        zsq = cart.z ** 2

        s = (xsq + ysq) ** 0.5

        lon = np.arctan2(cart.y, cart.x)
        lat = np.arctan2(cart.z, s)

        return UnitSphericalRepresentation(lon=lon, lat=lat)


class PhysicsSphericalRepresentation(BaseRepresentation):
    """
    Representation of points in 3D spherical coordinates (using the physics
    convention of using ``phi`` and ``theta`` for azimuth and inclination
    from the pole).

    Parameters
    ----------
    phi, theta : `~astropy.units.Quantity` or str
        The azimuth and inclination of the point(s). The input values are
        passed to the `~astropy.coordinates.Angle`, so any valid
        input for these classes is acceptable. This includes
        `~astropy.units.Quantity` instances, strings, and lists of strings.

    distance : `~astropy.units.Quantity`
        The distance to the point(s). If the distance is a length, it is
        passed to the :class:`~astropy.coordinates.Distance` class, otherwise
        it is passed to the :class:`~astropy.units.Quantity` class.

    copy : bool, optional
        If True arrays will be copied rather than referenced.
    """

    def __init__(self, phi, theta, distance, copy=True):

        # Let the Longitude and Latitude classes deal with e.g. parsing
        phi = Angle(phi, copy=copy)
        theta = Angle(theta, copy=copy)

        if isinstance(distance, u.Quantity) and distance.unit.physical_type == 'length':
            distance = Distance(distance, copy=copy)
        else:
            distance = u.Quantity(distance, copy=copy)

        try:
            phi, theta, distance = broadcast_quantity(phi, theta, distance, copy=copy)
        except ValueError:
            raise ValueError("Input parameters phi, theta, and distance cannot be broadcast")

        self._phi = phi
        self._theta = theta
        self._distance = distance

    @property
    def phi(self):
        """
        The azimuth of the point(s).
        """
        return self._phi

    @property
    def theta(self):
        """
        The elevation of the point(s).
        """
        return self._theta

    @property
    def distance(self):
        """
        The distance from the origin to the point(s).
        """
        return self._distance

    def represent_as(self, other_class):
        # Take a short cut if the other clsss is a spherical representation
        if other_class is SphericalRepresentation:
            return SphericalRepresentation(lon=self.phi,
                                           lat=90 * u.deg - self.theta,
                                           distance=self.distance)
        else:
            return super(PhysicsSphericalRepresentation, self).represent_as(other_class)

    def to_cartesian(self):
        """
        Converts spherical polar coordinates to 3D rectangular cartesian
        coordinates.
        """

        # We need to convert Distance to Quantity to allow negative values.
        if isinstance(self.distance, Distance):
            d = self.distance.view(u.Quantity)
        else:
            d = self.distance

        x = d * np.sin(self.theta) * np.cos(self.phi)
        y = d * np.sin(self.theta) * np.sin(self.phi)
        z = d * np.cos(self.theta)

        return CartesianRepresentation(x=x, y=y, z=z)

    @classmethod
    def from_cartesian(cls, cart):
        """
        Converts 3D rectangular cartesian coordinates to spherical polar
        coordinates.
        """

        xsq = cart.x ** 2
        ysq = cart.y ** 2
        zsq = cart.z ** 2

        r = (xsq + ysq + zsq) ** 0.5
        s = (xsq + ysq) ** 0.5

        phi = np.arctan2(cart.y, cart.x)
        theta = np.arctan2(s, cart.z)

        return PhysicsSphericalRepresentation(phi=phi, theta=theta, distance=r)


class CylindricalRepresentation(BaseRepresentation):
    """
    Representation of points in 3D cylindrical coordinates.

    Parameters
    ----------
    rho : `~astropy.units.Quantity`
        The distance from the z axis to the point(s).

    phi : `~astropy.units.Quantity` or str
        The azimuth of the point(s). The input is passed to the
        `~astropy.coordinates.Angle` class, so any valid input for that class
        is acceptable

    z : `~astropy.units.Quantity`
        The z coordinate(s) of the point(s)

    copy : bool, optional
        If True arrays will be copied rather than referenced.
    """

    def __init__(self, rho, phi, z, copy=True):

        rho = u.Quantity(rho, copy=copy)
        phi = Angle(phi, copy=copy)
        z = u.Quantity(z, copy=copy)

        if not (rho.unit.physical_type == z.unit.physical_type):
            raise u.UnitsError("rho and z should have matching physical types")

        try:
            rho, phi, z = broadcast_quantity(rho, phi, z, copy=copy)
        except ValueError:
            raise ValueError("Input parameters rho, phi, and z cannot be broadcast")

        self._rho = rho
        self._phi = phi
        self._z = z

    @property
    def rho(self):
        """
        The distance of the point(s) from the z-axis.
        """
        return self._rho

    @property
    def phi(self):
        """
        The azimuth of the point(s).
        """
        return self._phi

    @property
    def z(self):
        """
        The height of the point(s).
        """
        return self._z

    @classmethod
    def from_cartesian(cls, cart):
        """
        Converts 3D rectangular cartesian coordinates to cylindrical polar
        coordinates.
        """

        rho = np.sqrt(cart.x ** 2 + cart.y ** 2)

        phi = np.zeros(cart.x.shape) * u.deg
        phi[rho > 0] = np.arctan2(cart.y, cart.x)

        z = cart.z

        return CylindricalRepresentation(rho=rho, phi=phi, z=z)

    def to_cartesian(self):
        """
        Converts cylindrical polar coordinates to 3D rectangular cartesian
        coordinates.
        """
        x = self.rho * np.cos(self.phi)
        y = self.rho * np.sin(self.phi)
        z = self.z

        return CartesianRepresentation(x=x, y=y, z=z)
