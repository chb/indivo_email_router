Indivo Email Router
===================

Installation
------------

* Pre-reqs:

  * python v2.6 or later

  * django v1.2 or later

  * apache v2 with mod_wsgi
  
  * python-setuptools

* RabbitMQ v2.7.0:

  * Install the package::

      wget http://www.rabbitmq.com/releases/rabbitmq-server/v2.7.0/rabbitmq-server_2.7.0-1_all.deb
      dpkg -i rabbitmq-server_2.7.0-1_all.deb
      rm rabbitmq-server_2.7.0-1_all.deb
   
  * Add the indivo_email_router user and pick a password (you'll need to update ``settings.RABBITMQ_USER`` and
    ``settings.RABBITMQ_PASSWORD`` to match these later, so don't forget them)::
  
      sudo rabbitmqctl add_user indivo_email_router YOUR_PASSWORD

  * Add a rabbitmq virtual host to use (corresponding to ``settings.RABBITMQ_VHOST``)::

      sudo rabbitmqctl add_vhost indivo_messages

  * Set permissions for the indivo_email_router user in the virtual host::
  
      sudo rabbitmqctl set_permissions -p myvhost myuser ".*" ".*" ".*"

  * Make sure rabbitmq is running::
  
      sudo rabbitmq-server
  
* Celery v2.4.5:

  * Install the package::

      sudo easy_install -U celery

  * Set up a celery user/group::
  
      sudo useradd celery

  * Copy init_scripts/configuration.default to init_scripts/contifuration and edit,
    setting ``INDIVO_EMAIL_ROUTER_HOME`` to the full path to your installation.

  * Copy init scripts over to your machine (UBUNTU SPECIFIC)::
  
      sudo cp init_scripts/celery* /etc/init.d/
      sudo cp init_scripts/configuration /etc/default/celeryd

* Indivo Integration:

  * Make sure that you have exchanged an oauth consumer key and secret with a valid instance of
    Indivo Server, and that this app is registered at that instance with as an autonomous app
    with the key and secret. See 
    http://wiki.chip.org/indivo/index.php/Indivo_Authentication#User_Applications_.28PHAs.29A 
    for more details on that exchange. A sample XML definition of the app for Indivo Server might 
    look like::

      <user_app name="Indivo Email Router" email='indivo_email_router@apps.indivo.org'>
        <consumer_key>YOUR_KEY</consumer_key>
        <secret>YOUR_SECRET</secret>
        <is_autonomous>True</is_autonomous>
        <autonomous_reason>This app connects to your record to load new emails into it while you sleep.</autonomous_reason>
        <has_ui>False</has_ui>
      </user_app>


Running the Email Router
------------------------

* Copy settings.py.default to settings.py and edit the settings, especially:

  * ``APP_HOME``: The location of this install

  * ``EMAIL_POLL_INTERVAL``: The number of seconds between checks for new emails

  * ``INDIVO_SERVER_LOCATION``: The location of a running Indivo Server install

  * ``INDIVO_SERVER_OAUTH``: The credentials to connect as the indivo_email_router app.

  * ``RABBITMQ_*``: The user, password, and virtual host you set up for rabbitmq above

* Set up Apache to serve the Django application (similar to Indivo, see 
  http://wiki.chip.org/indivo/index.php/HOWTO:_install_Indivo_X#Running_on_Apache ), or run the Django 
  development servers::

    python manage.py runserver 8003

* Start the message poller::

    ./routerctl start
