from django.conf import settings

MAPS_API_KEY = getattr(settings, 'LOCATIONS_MAPS_API_KEY', None)
GEOCODER_BACKEND = getattr(settings, 'LOCATIONS_GEOCODER_BACKEND', 'Google')
