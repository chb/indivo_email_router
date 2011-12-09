from django.conf.urls.defaults import *
from views import *

urlpatterns = patterns('',
   # register access tokens
   (r'^register$', register),
)
