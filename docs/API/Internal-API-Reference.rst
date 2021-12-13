Internal API-Reference
======================
The interal API-Reference of the wrapper. This shows all internal methods and classes used
throughout the wrapper.

.. danger::

   All methods and classes shown here are used internally, users shouldn't be touching
   these and doing so can break the wrapper.


HTTP Internals
--------------
.. currentmodule:: lefi.http

Endpoint Routes
~~~~~~~~~~~~~~~
.. autoclass:: Route
    :members:

HTTPClient
~~~~~~~~~~
.. autoclass:: HTTPClient
    :members:

HTTP Ratelimiter
~~~~~~~~~~~~~~~~
.. note::

   This ratelimiter uses semaphores set to X-Ratelimit-Limit per bucket. Thus allowing for
   concurrent requests.

.. autoclass:: lefi.ratelimiter.Ratelimiter
    :members:

Gateway Internals
-----------------
.. currentmodule:: lefi.ws

Max Concurrency Ratelimiter
~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: lefi.ws.ratelimiter.Ratelimiter
    :members:

BaseWebsocketClient
~~~~~~~~~~~~~~~~~~~
.. autoclass:: BaseWebsocketClient
    :members:

WebSocketClient
~~~~~~~~~~~~~~~
.. autoclass:: WebSocketClient
    :show-inheritance:
    :inherited-members:
    :members:

Sharded Websocket
~~~~~~~~~~~~~~~~~
.. autoclass:: Shard
    :show-inheritance:
    :inherited-members:
    :members:

State Internals
---------------
.. currentmodule:: lefi.state

State Handler
~~~~~~~~~~~~~
.. autoclass:: State
    :members:

Object Cache
~~~~~~~~~~~~
.. autoclass:: Cache
    :exclude-members: __init__, __new__
    :inherited-members:
    :members:

Operation Codes
---------------

Websocket OpCodes
~~~~~~~~~~~~~~~~~
.. autoclass:: lefi.ws.OpCodes
    :show-inheritance:
    :inherited-members:
    :members:
