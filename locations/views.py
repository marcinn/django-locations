import geopy.distance
import geopy.units
import datetime


from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from locations.models import Location
from friends.models import Friendship
from locations.forms import LocationForm, CheckinForm
from django.utils.translation import ugettext as _
from django.core.exceptions import ImproperlyConfigured
from django.views.generic.list_detail import object_list, object_detail
from locations import settings

try:
    from notification import models as notification
except ImportError:
    notification = None


def lazy_key():
    return settings.MAPS_API_KEY


@login_required
def your_locations(request, template_name=None, extra_context=None,
        queryset=None, **kw):
    """
    Shows the list of locations a user checked in
    """
    queryset = queryset or Location.objects.all()
    queryset = queryset.filter(user=request.user)

    context = extra_context or {}
    context.update({
        'location_form': LocationForm(),
        'YAHOO_MAPS_API_KEY': lazy_key(), # bc
        'MAPS_API_KEY': lazy_key(),
    })
    return object_list(request, extra_context=context, queryset=queryset,
            template_name=template_name or 'locations/your_locations.html',
            **kw)


@login_required
def new(request):
    """
    Gets data from the search form and tries to geocode that location.
    I am passing an invisible checkin form which contains
    'value={{ location.place }}' and other attributes so that data can be passed
    back to the view. I didn't know a better way of doing it.
    """

    context = {
            'YAHOO_MAPS_API_KEY': lazy_key(), # bc
            'MAPS_API_KEY': lazy_key(),
            }
    if request.method == 'POST':
        location_form = LocationForm(request.POST)
        if location_form.is_valid():
            p = location_form.cleaned_data['place']
            try:
                (place, (lat, lng)) = list(Location.objects.geocode(p, multiple=True))[0]
                # Actually returns more than one result but I am taking only the
                # first result
            except Location.DoesNotExist:
                request.user.message_set.create(
                    message=_('Location not found, Try something else.'))
                context['location_form'] = location_form
                return render_to_response("locations/new.html",
                    context,
                    context_instance=RequestContext(request)
                )
            context.update({
                'location': {'place': place, 'latitude': lat, 'longitude': lng},
                'checkin_form': CheckinForm(),
            })
            return render_to_response("locations/checkin.html",
                context,
                context_instance=RequestContext(request)
            )
        else:
            return HttpResponseRedirect(reverse('locations.views.your_locations'))
    else:
        return HttpResponseRedirect(reverse('locations.views.your_locations'))


@login_required
def checkin(request):
    """
    When user clicks checkin, we write into the model Location with user, place,
    latitude and longitude info. Of course, along with the datetime of the checkin.
    """
    if request.method == 'POST':
        checkin_form = CheckinForm(request.POST)
        if checkin_form.is_valid():
            c = Location(
                place=checkin_form.cleaned_data['place'],
                latitude=checkin_form.cleaned_data['latitude'],
                longitude=checkin_form.cleaned_data['longitude'],
                user=request.user,
                time_checkin=datetime.datetime.now()
            )
            c.save()
            return HttpResponseRedirect(reverse('locations.views.your_locations'))
    return HttpResponseRedirect(reverse('locations.views.new'))


@login_required
def friends_checkins(request):
    user = request.user
    friends = Friendship.objects.friends_for_user(user)
    context = {
        'friends': friends,
        'YAHOO_MAPS_API_KEY': lazy_key(), # bc
        'MAPS_API_KEY': lazy_key(),
    }
    return render_to_response("locations/friends_checkins.html",
        context,
        context_instance=RequestContext(request)
    )


@login_required
def nearby_checkins(request, distance=None):
    user = request.user
    context = {
            'YAHOO_MAPS_API_KEY': lazy_key(), # bc
            'MAPS_API_KEY': lazy_key(),
            }
    if user.location_set.latest():
        place = user.location_set.latest()
        distance = distance or settings.DISTANCE

        queryset = Location.objects.all().nearest(place, distance,
                unit=settings.DISTANCE_UNITS)

        # Filtering the query set with an area of rough distance all the sides
        locations = []
        for location in queryset:
            if location.latitude and location.longitude:
                exact_distance = geopy.distance.distance(
                    (place.latitude, place.longitude),
                    (location.latitude, location.longitude)
                )
                if getattr(exact_distance, settings.DISTANCE_UNITS) <= distance:
                    locations.append(location)
        queryset = queryset.filter(id__in=[l.id for l in locations])
        context['queryset'] = queryset.exclude(user=request.user)
        return render_to_response("locations/nearby_checkins.html",
            context,
            context_instance=RequestContext(request)
        )
    else:
        request.user.message_set.create(
            message=_("You haven't checked in any location."))
        return render_to_response("locations/nearby_checkins.html",
            context,
            context_instance=RequestContext(request)
        )


def detail(request, id=None, template_name=None, 
        extra_context=None, queryset=None):
    """
    display location detail
    """
    queryset = queryset or Location.objects.all()
    extra_context = extra_context or {}
    if request.user.is_authenticated():
        extra_context['your_nearest_locations'] = Location.objects.filter(
                user=request.user).nearest(queryset.get(pk=id))
    
    return object_detail(request, object_id=id, queryset=queryset,
            template_name = template_name, extra_context=extra_context)


@login_required
def bookmark(request, id):
    """
    create clone of other location and assign to logged user
    """
    try:
        loc = Location.objects.get(pk=id)
        new_loc = Location.objects.create(user=request.user,
            place=loc.place, latitude=loc.latitude,
            longitude=loc.longitude, geocoded_place=loc.geocoded_place)
        new_loc.save()
        request.user.message_set.create(
            message=_("Location was saved."))
        return HttpResponseRedirect(new_loc.get_absolute_url())
    except Location.DoesNotExist:
        raise Http404


