# Author : Yashh (www.yashh.com)
# Since I would be just showing a list of checkins, I haven't included any extra
# methods on the model.


from urllib2 import HTTPError
import unicodedata
from django.db import models
from django.db.models.query import QuerySet, Q
from django.contrib.auth.models import User
import geopy

from locations import settings

try:
    geocoder = getattr(__import__('geopy.geocoders', globals(), locals(),
    [settings.GEOCODER_BACKEND],), settings.GEOCODER_BACKEND)(settings.MAPS_API_KEY)
except ImportError:
    raise ValueError('Invalid LOCATION_GEOCODER_BACKEND: %s'
            % settings.GEOCODER_BACKEND)


class LocationQuerySet(QuerySet):
    def nearest(self, location, tolerance=0, unit='kilometers'):
        """
        Filter result to nearest locations.

        location can be:
          - (lat, lon) tuple
          - Location model instance
          - Location model pk
          - or string with location name

        You can use optional tolerance arg measured in units
        """

        kw = {unit: tolerance}
        rough_distance = geopy.units.degrees(
            arcminutes=geopy.units.nm(**kw)) * 2

        if isinstance(location, tuple):
            lat, lon = location
        elif isinstance(location, Location):
            lat, lon = location.latitude, location.longitude
        elif isinstance(location, (str, unicode)):
            location = Location.objects.get_by_name(location)
            lat, lon = location.latitude, location.longitude
        elif isinstance(location, int):
            location = Location.objects.get(pk=location)
            lat, lon = location.latitude, location.longitude
        else:
            raise ValueError('invalid location argument')

        return self.filter(
            latitude__range=(lat - rough_distance,
                lat + rough_distance),
            longitude__range=(lon - rough_distance,
                lon + rough_distance))

    def named(self, name):
        """
        returns locations matching name
        """
        normalized = normalize_location_name(name)
        return self.filter(
                Q(place__istartswith=normalized)\
                | Q(geocoded_place__istartswith=normalized))


class LocationManager(models.Manager):
    def get_query_set(self):
        return LocationQuerySet(self.model)

    def get_by_name(self, name):
        """
        returns location recognized by name
        """
        return self.get_query_set().named(name).get()

    def geocode(self, location, multiple=False):
        """
        wrapper for geocoder

        location can be:
          - Location model
          - Location pk
          - location string
          - (lat, lon) tuple

        returns (location_name, (lat, lon)) tuple
        """

        if isinstance(location, Location):
            place = location.place
        elif isinstance(location, (str, unicode)):
            place = location
        elif isinstance(location, tuple):
            place = u'%f, %f' % location
        elif isinstance(location, int):
            place = self.get_query_set().get(pk=location).place
        else:
            raise ValueError('invalid location argument')

        try:
            place = unicodedata.normalize('NFKD',
                    unicode(place)).encode('ascii', 'ignore')
            return geocoder.geocode(place, exactly_one=not multiple)
        except HTTPError:
            return self.model.DoesNotExist


class Location(models.Model):
    user = models.ForeignKey(User)
    time_checkin = models.DateTimeField(auto_now_add=True)
    place = models.CharField(max_length=100)
    geocoded_place = models.CharField(max_length=100, null=True,
            blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    objects = LocationManager()
  
    class Meta:
        ordering = ('-time_checkin',)
        get_latest_by = 'time_checkin'

    def __repr__(self):
        return 'Location object [%d, "%s", (%f, %f)]' % (
                self.pk, self.place, self.latitude,
                self.longitude)

    def __unicode__(self):
        return self.place

    def save(self, force_insert=None, force_update=None):
        """
        save Location instance
        automatically geocode place if lat/long were not provided
        """

        # geocode place if lat nor lon aren't set
        if not self.latitude or not self.longitude:
            self.geocoded_place, (self.latitude,
            self.longitude) = Location.objects.geocode(self.place)

        # normalize place name
        if not self.pk:
            self.place = normalize_location_name(self.place)

        return super(Location, self).save(force_insert, force_update)

    @models.permalink
    def get_absolute_url(self):
        return ('loc_detail', (self.id,), {})


def normalize_location_name(name):
    """
    returns normalized location string
    """
    return u', '.join([p.strip() for p in name.split(',')])
