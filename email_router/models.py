"""
.. module:: email_router.models
   :synopsis: Django Model Definitions for the Indivo Email Router App

.. moduleauthor:: Daniel Haas <daniel.haas@post.harvard.edu>

"""

from django.db import models
from urlparse import parse_qs

# generate the right meta class
APP_LABEL = 'email_router'

class AccessToken(models.Model):
  record_id = models.CharField(max_length=50, primary_key=True)
  token_string = models.CharField(max_length=50)

  def __str__(self):
    return self.token_string

  @property
  def parsed(self):
    p = parse_qs(self.token_string)
    return dict( [(k,v) if len(v) > 1 else (k, v[0])
                  for k,v in p.items()])

  class Meta:
    app_label = APP_LABEL
