Internal API-Reference
======================

REST
----

Route
~~~~~
.. autoclass:: lefi.http.Route
    :members:

HTTPClient
~~~~~~~~~~
.. autoclass:: lefi.http.HTTPClient
    :members:

Ratelimiter
~~~~~~~~~~~
.. autoclass:: lefi.ratelimiter.Ratelimiter
    :members:

Gateway
-------

Websocket clients
~~~~~~~~~~~~~~~~~

Base websocket client
^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: lefi.ws.basews.BaseWebsocketClient
    :members:

Sharded websocket client
^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: lefi.ws.shard.Shard
    :members:
    :inherited-members:

Websocket client
^^^^^^^^^^^^^^^^
.. autoclass:: lefi.ws.wsclient.WebSocketClient
    :members:
    :inherited-members:

Cache
~~~~~
.. autoclass:: lefi.state.Cache
    :members:
    :show-inheritance:
    :inherited-members:

State
~~~~~
.. autoclass:: lefi.state.State
    :members:

Max concurreny Ratelimiter
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: lefi.ws.ratelimiter.Ratelimiter
   :members:

OpCodes
~~~~~~~
.. autoclass:: lefi.ws.opcodes.OpCodes
    :members:
    :inherited-members:
