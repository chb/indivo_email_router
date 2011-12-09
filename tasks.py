"""
.. module:: tasks
   :synopsis: Celery tasks for polling mail services and routing messages to Indivo

.. moduleauthor:: Daniel Haas <daniel.haas@post.harvard.edu>

"""

from celery.task import task
from celery.task.sets import subtask
from indivo_client_py.lib.client import IndivoClient
import uuid

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings

from email_router.models import AccessToken

@task(ignore_result=True)
def get_new_emails():
    """ Read new emails from an email server, and schedule them for delivery to Indivo.

    Parsing of the emails is handled in the subtask (deliver_email_to_indivo()).

    """

    # TODO
    logger = get_new_emails.get_logger()
    logger.info('getting new emails...')
    emails = ['a', 'b', 'c']

    # Schedule a task to deliver each message to Indivo
    for email in emails:
        subtask(deliver_email_to_indivo).delay(email)

@task(ignore_result=False, max_retries=5)
def deliver_email_to_indivo(email):
    """ Send an email to indivo's inbox via the messaging API.

    The email must contain enough information to identify the
    recipient record for the message.

    """

    logger = deliver_email_to_indivo.get_logger()
    logger.info(email)

    # get the record id for the message
    logger.info('getting record id from email address...')
    record_id = get_record_from_email(email)

    # do we have an access token for the record
    logger.info('Looking up access token for record %s'%record_id)
    token = lookup_token(record_id)
    if not token:
        logger.error('Dropping message... unregistered record_id %s'%record_id)
        raise IndivoRecordNotFound(record_id)

    # get the Indivo client
    client = get_indivo_client(token=token.token_string)

    # send the message
    message_id = str(uuid.uuid4())
    data = {
        'subject':'TEST SUBJECT',
        'body': 'HERE IS A MESSAGE',
        'body_type': 'markdown',
        'severity':'high',
        }

    logger.info('Sending message to Indivo...')
    try:
        response = client.message_record(record_id=record_id, message_id=message_id, data=data).response
        logger.info('Got response! %s'%str(response))
    except Exception, e:
        logger.error('Got error! %s'%str(e))
        raise IndivoException(str(e))

    status = response['response_status']
    if status == 200:
        logger.info('Success! Message delivered')

    # 403 and 404 are errors, because they mean our database is corrupt
    # or out of date. Fail if this happens.
    elif status == 403:
        logger.error('Message not delivered. Bad token.')
        raise IndivoAuthenticationError(token.token_string, settings.INDIVO_SERVER_OAUTH)
    elif status == 404:
        logger.error('Message not delivered. Bad Record id.')
        raise IndivoRecordNotFound

    # 400 and other are warnings, because the problem was either on Indivo's end,
    # or it was the email content. Retry if this happens, but not too many times.
    elif status == 400:
        logger.warning('Message not delivered. Invalid message content: %s Retrying...'%data['body'])
        exc = IndivoValidationError('Invalid Message Content: %s'%data['body'])
        deliver_email_to_indivo.retry(exc=exc)
    else:
        logger.warning('Message not delivered. Unknown error: statuscode %s. Retrying...'%status)
        exc = IndivoException('Unknown Error: statuscode %s.'%status)
        deliver_email_to_indivo.retry(exc=exc)

def get_indivo_client(token=None):
    client = IndivoClient(settings.INDIVO_SERVER_OAUTH['consumer_key'],
                          settings.INDIVO_SERVER_OAUTH['consumer_secret'],
                          settings.INDIVO_SERVER_LOCATION)
    if token:
        client.update_token(token)
    return client

def lookup_token(record_id):
    try:
        return AccessToken.objects.get(record_id=record_id)
    except AccessToken.DoesNotExist:
        return None

def get_record_from_email(email):
    # TODO
    return '1b384447-3fe0-40f6-b03e-5009f3726c7f'


##############
# Exceptions #
##############
class IndivoException(Exception):
    pass

class IndivoAuthenticationError(IndivoException):
    def __init__(self, token_string, oauth_credentials):
        self.token_string = token_string
        self.oauth_credentials = oauth_credentials
        super(IndivoAuthenticationError, self).__init__('Indivo Authentication Failure: bad token %s. Credentials were %s'%(token_string, oauth_credentials))

class IndivoRecordNotFound(IndivoException):
    def __init__(self, record_id):
        self.record_id = record_id
        super(IndivoRecordNotFound, self).__init__('Indivo Record Not Found exception: no record %s'%record_id)

class IndivoValidationError(IndivoException):
    pass
