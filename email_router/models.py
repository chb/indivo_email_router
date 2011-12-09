"""
.. module:: email_router.models
   :synopsis: Django Model Definitions for the Indivo Email Router App

.. moduleauthor:: Daniel Haas <daniel.haas@post.harvard.edu>

"""

from django.db import models

# generate the right meta class
APP_LABEL = 'email_router'

class AccessToken(models.Model):
  record_id = models.CharField(max_length=50, primary_key=True)
  token_string = models.CharField(max_length=50)

  def __str__(self):
    return self.token_string

  class Meta:
    app_label = APP_LABEL
