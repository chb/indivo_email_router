"""
.. module:: tasks
   :synopsis: Celery tasks for polling mail services and routing messages to Indivo

.. moduleauthor:: Daniel Haas <daniel.haas@post.harvard.edu>

"""

from celery.task import task
from celery.task.sets import subtask
from indivo_client_py.lib.client import IndivoClient
import uuid, imaplib, email

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings

from email_router.models import AccessToken

DEFAULT_MAIL_PORTS = { 
    'imap': 143,
    'imap_ssl': 993,
    }

@task(ignore_result=True)
def get_new_emails():
    """ Read new emails from an email server, and schedule them for delivery to Indivo.

    Parsing of the emails is handled in the subtask (deliver_email_to_indivo()).

    """

    # TODO
    logger = get_new_emails.get_logger()
    logger.info('connecting to the mail server...')
    conn = mail_server_connect()

    try:
        logger.info('getting new emails...')
        typ, message_id_list = conn.search(None, 'UNSEEN')
        if typ != 'OK':
            raise MailServerException("Error reading new messages: %s" % message_id_list[0])
        
        message_ids = [m for m in message_id_list[0].split(" ") if m]
        logger.info('%s new messages found' % len(message_ids))
        for m_id in message_ids:
            logger.info('fetching message with id %s' % m_id)
            typ, msg_data = conn.fetch(m_id, '(RFC822)')
            if typ != 'OK':
                raise MailServerException("Error fetching message %s: %s" % (m_id, msg_data[0]))

            parsed_email = email.message_from_string(msg_data[0][1])
            if deliver_email_p(parsed_email):
                
                # Schedule a task to deliver the message to Indivo                
                logger.info('New email! scheduling for delivery...') 
                subtask(deliver_email_to_indivo).delay(parsed_email)

            else:
                logger.warning('Rejecting message from %s: Not in approved senders list'% parsed_email.get('From', ''))
    except conn.error as e:
        logger.error(str(e))
    finally:
        logger.info('disconnecting from mail server...')
        mail_server_disconnect(conn)

@task(ignore_result=False, max_retries=5)
def deliver_email_to_indivo(parsed_email):
    """ Send an email to indivo's inbox via the messaging API.

    The email must contain enough information to identify the
    recipient record for the message.

    """

    logger = deliver_email_to_indivo.get_logger()

    # get the record id for the message
    logger.info('getting record id from email message...')
    record_id = get_record_from_email(parsed_email)

    # do we have an access token for the record
    logger.info('Looking up access token for record %s'%record_id)
    token = lookup_token(record_id)
    if not token:
        logger.error('Dropping message... unregistered record_id %s'%record_id)
        raise IndivoRecordNotFound(record_id)

    # get the Indivo client
    client = get_indivo_client(token=token)

    # send the message
    if parsed_email.is_multipart():
        logger.error("Dropping message... Multipart messages not supported.")
        return
#        message_data = ''
#        for part in parsed_email.walk():
#            message_data += part.get_payload()
    else:        
        message_data = parsed_email.get_payload()

    message_id = str(uuid.uuid4())
    data = {
        'subject':parsed_email.get('Subject', '[NO SUBJECT]'),
        'body': message_data or '[NO BODY]',
        'body_type': 'markdown',
        'severity':'high',
        }

    logger.info('Sending message to Indivo...')
    try:
        response = client.message_record(record_id=record_id, message_id=message_id, data=data).response
        logger.info('Got response!')
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
        raise IndivoAuthenticationError(token, settings.INDIVO_SERVER_OAUTH)
    elif status == 404:
        logger.error('Message not delivered. Bad Record id.')
        raise IndivoRecordNotFound(record_id)

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

def mail_server_connect():
    defaults = {'protocol':'imap',
                'mailbox':'INBOX',
                }

    defaults.update(settings.INBOUND_MAIL_SERVER_SETTINGS)
    if not defaults.get('port', None):
        defaults['port'] = DEFAULT_MAIL_PORTS[defaults['protocol']]

    if defaults['protocol'] == 'imap':
        conn = imaplib.IMAP4(defaults['host'], defaults['port'])
        conn.login(defaults['user'], defaults['password'])
        typ, data = conn.select(defaults['mailbox'])
        if typ == 'NO':
            mail_server_disconnect(conn)
            raise MailServerException("Tried to use nonexistent mailbox %s"%defaults['mailbox'])

    elif defaults['protocol'] == 'imap_ssl':
        conn = imaplib.IMAP4_SSL(defaults['host'], defaults['port'])
        conn.login(defaults['user'], defaults['password'])
        typ, data = conn.select(defaults['mailbox'])
        if typ == 'NO':
            mail_server_disconnect(conn)
            raise MailServerException("Tried to use nonexistent mailbox %s"%defaults['mailbox'])
    else:
        raise MailServerException("Unsupported protocol: %s" % defaults['protocol'])

    return conn

def mail_server_disconnect(connection):
    try:
        connection.close()
    except connection.error:
        pass

    connection.logout()
    return

def deliver_email_p(parsed_email):
    """ Given a message, determine whether we should try delivering it to Indivo.

    Criteria are:
    * The ``accepted_senders`` parameter in settings.y
    * Whether the from address is formatted appropriately.

    """
    
    from_addr = email.utils.parseaddr(parsed_email.get('From'))[1]
    accepted_addrs = settings.INBOUND_MAIL_SERVER_SETTINGS.get('accepted_senders', None)
    if accepted_addrs and from_addr not in accepted_addrs:
        return False

    if not get_record_from_email(parsed_email):
        return False

    return True
    
def get_indivo_client(token=None):
    client = IndivoClient(settings.INDIVO_SERVER_OAUTH['consumer_key'],
                          settings.INDIVO_SERVER_OAUTH['consumer_secret'],
                          settings.INDIVO_SERVER_LOCATION)
    if token:
        client.update_token(token)

    return client

def lookup_token(record_id):
    try:
        return AccessToken.objects.get(record_id=record_id).parsed
    except AccessToken.DoesNotExist:
        return None

def get_record_from_email(parsed_email):
    """ Parse an indivo record_id string from an incoming email.

    Currently, the implementation assumes that the email is addressed to 'RECORD_ID@this_domain', and that
    RECORD_ID is a valid UUID string.

    The implementation is also limited to one address in the TO: field of incoming emails.

    """
    
    # Note: this won't work if there are multiple TO addresses. Consider building in the logic to handle that case.
    to_address = email.utils.parseaddr(parsed_email.get('To'))[1]
    try:
        record_id = to_address.split('@')[0]
        record_uuid = uuid.UUID(record_id) # see if the address parses as a valid UUID
    except ValueError:
        return None
    return record_id

##############
# Exceptions #
##############
class MailServerException(Exception):
    pass

class IndivoException(Exception):
    pass

class IndivoAuthenticationError(IndivoException):
    def __init__(self, token_dict, oauth_credentials):
        self.token_dict = token_dict
        self.oauth_credentials = oauth_credentials
        super(IndivoAuthenticationError, self).__init__('Indivo Authentication Failure: bad token %s. Credentials were %s'%(token_dict, oauth_credentials))

class IndivoRecordNotFound(IndivoException):
    def __init__(self, record_id):
        self.record_id = record_id
        super(IndivoRecordNotFound, self).__init__('No record %s'%record_id)

class IndivoValidationError(IndivoException):
    pass
