"""
.. module:: email_router.views
   :synopsis: Django View Functions for the Indivo Email Router App

.. moduleauthor:: Daniel Haas <daniel.haas@post.harvard.edu>

"""

from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseNotAllowed
from email_router.models import AccessToken

def register(request):
    """ Register a new user for email routing.

    **ARGS**:

    * *request*: The :py:class:`~django.http.HttpRequest` object associated with the incoming request.
      ``request.POST`` must contain:

      * *indivo_record_id*: The new user's indivo record id

      * *indivo_access_token*: A valid access token for this app to reach the user's record.

    **RETURNS**:
    
    * :http:statuscode:`200` on success.
    
    * :http:statuscode:`400` if either ``request.POST`` parameter is missing.

    * :http:statuscode:`405` if the request method wasn't :http:method:`post`.
    
    """

    if request.method.lower() != 'post':
        return HttpResponseNotAllowed(['POST'])
    
    # Get the params
    record_id = request.POST.get('indivo_record_id', None)
    token_str = request.POST.get('indivo_access_token', None)

    if not record_id or not token_str:
        return HttpResponseBadRequest()
    
    # Now store them
    access_token, created_p = AccessToken.objects.get_or_create(record_id=record_id, 
                                                                defaults={'token_string':token_str})
    
    # if we've already registered this user, update the accesstoken
    if not created_p:
        access_token.token_string = token_str
        access_token.save()

    return HttpResponse('<ok/>')
