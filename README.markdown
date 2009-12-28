This is a fork of Brian Rosner`s django-locations.

The most important goals:

* remove django-friends dependency (pinax)
* add location managers (move some code from views to managers)
* add support for more map APIs (original depends on yahoo maps)

Dependencies
============

* geopy (http://code.google.com/p/geopy/)


Usage
=====

Settings
--------

In your project settings you can set:

* LOCATIONS_MAPS_API_KEY  
  (your maps backend API key, default: None)

* LOCATIONS_GEOCODER_BACKEND   
  (valid geocoder class name supported by pygeo, ie. Google, Yahoo, default: Google)

Geocoding
---------

    from locations.models import Location
    Location.objects.geocode('Mount Everest')
    >>> (u'Mount Everest, Nepal', (27.98002, 86.921543))`

Multiple result:

    [loc for loc in Location.objects.geocode('Nile', multiple=True)]
    >>>
     [(u'Nile, WA 98937, USA', (46.8206761, -120.939522)),
      (u'Nile, MS 39051, USA', (32.945964799999999, -89.516739900000005)),
      (u'Nile, OH, USA', (38.684979900000002, -83.186335799999995)),
      (u'Nile, Summersville, WV 26651, USA',
       (38.303893600000002, -80.732369899999995)),
      (u'Nile, Sudan', (21.167508099999999, 30.658815700000002)),
      (u'\u0627\u0644\u0646\u064a\u0644, Sudan',
       (20.049753800000001, 30.581151500000001)),
      (u'Nile, Sudan', (18.5674697, 31.957265100000001)),
      (u'Nile, Sudan', (17.0837599, 33.691687700000003)),
      (u'Nile, Sudan', (19.5717532, 30.396868999999999))]


Create locations
----------------

    from locations.models import Location, User
    user = User.objects.get(username='admin')

    loc = Location.objects.create(user=user, place='New York, USA')
    loc.save()
  

Geocoding is automatically called during save, if latitude nor 
longitude properties are not set.


Search locations
----------------

Search by name:

    Location.objects.all().named('Rycerka')
    >>> [Location object [4, "Rycerka, Polska", (49.447705, 19.077307)]]

Search nearest to another location:

    Location.objects.all().nearest('Rycerka')
    >>> [Location object [4, "Rycerka, Polska", (49.447705, 19.077307)]]

    # around 20 kilometers:
    Location.objects.all().nearest('Rycerka', tolerance=20)
     >>> [Location object [4, "Rycerka, Polska", (49.447705, 19.077307)], Location object [2, "Rycerzowa, Polska", (49.416667, 19.100000)]]

    # around 20 miles:
    Location.objects.all().nearest('Rycerka', tolerance=20, unit='miles')
    >>> [Location object [4, "Rycerka, Polska", (49.447705, 19.077307)], Location object [3, "Zawoja, Polska", (49.643930, 19.542495)], Location object [2, "Rycerzowa, Polska", (49.416667, 19.100000)]]


Nearest location can be:

* string or unicode with location name
* Location instance
* Location`s pk
* (lat, lon) tuple

