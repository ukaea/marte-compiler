
Installation & Configuration
############################

Installation
^^^^^^^^^^^^

To install the runner is quite simple, run the command:

.. code::
   
   curl https://git.ccfe.ac.uk/marte21/public/marte-compiler/-/raw/master/install.sh?inline=false | sudo bash

After this, the runner will be installed.

.. note:: You must have sudo privileges in order to install the runner service.

Configuring
^^^^^^^^^^^

In order to update the configuration of the runner you can change the configuration at:

.. code::

    /opt/martecompiler/settings.yml

After which, restart the service:

.. code::
   
   sudo systemctl restart martecompiler

Configuration Options:
**********************

* temp_directory: Directory from which executions are run, by default a system user named martecompilerrunner is created and it's home directory is used.
* http_port: HTTP Port from which new sessions are requested and executed.
* ftp_port: FTP Port for file transference within a sessions
* username: username to authenticate with the FTP Server.
* password: password for authenticating the user with the FTP Server.

.. note:: The FTP Server is hosted by the runner itself, like the HTTP server, the FTP sessions are only valid to the temp_directory and will not allow file transfers to happen outside of this directory.

**clean up routine:**

The clean up routine is a class within the runner which routinely deletes old outdated sessions to ensure a space is utilised on disk appropriately.

* period: How often to run the clean up cycle.
* keep_for: The age at which files get deleted - in seconds unless specified with time expressions.
* trim_to: The maximum size of the directory before the oldest files get deleted.

