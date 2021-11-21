.. currentmodule: lefi

API-Reference
=============
Models
------

Client
~~~~~~
.. autoclass:: lefi.client.Client
    :members:

Attachment
~~~~~~~~~~
.. autoclass:: lefi.attachments.Attachment
    :members:
    :show-inheritance:
    :inherited-members:

CDN Asset
~~~~~~~~~
.. autoclass:: lefi.attachments.CDNAsset
    :members:
    :show-inheritance:
    :inherited-members:

Errors
------
Client errors
~~~~~~~~~~~~~
.. autoexception:: lefi.errors.ClientException
    :inherited-members:

Voice errors
~~~~~~~~~~~~
.. autoexception:: lefi.errors.VoiceException
    :inherited-members:

.. autoexception:: lefi.errors.OpusNotFound
    :show-inheritance:

HTTP errors
~~~~~~~~~~~
.. autoexception:: lefi.errors.HTTPException
    :show-inheritance:
    :inherited-members:

.. autoexception:: lefi.errors.BadRequest
    :show-inheritance:

.. autoexception:: lefi.errors.Forbidden
    :show-inheritance:

.. autoexception:: lefi.errors.NotFound
    :show-inheritance:

.. autoexception:: lefi.errors.Unauthorized
    :show-inheritance:
