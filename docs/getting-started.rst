Getting started
===============

Installation
------------

To install this library you can use whatever package manager you prefer.
I suggest personally to use ``poetry``, a souped up virtual env with package management.

- Poetry
    .. code-block:: none

        poetry add lefi

- Pip
    .. code-block:: none

        pip install lefi


Basic introduction
------------------

1. Setting event callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^
This library focuses on dispatching events and receiving events.
Heres an example for setting an event callback.

.. code-block:: python3

    import lefi

    client = lefi.Client("TOKEN")

    @client.on("message_create")
    async def on_message(message: lefi.Message) -> None:
        print(f"Got a message! {message.content}")

    client.run()

In the example above, we *construct* a new client, then use the decorator :meth:`.Client.on` to register
a callback to the event ``message_create``. Everytime a new message is created the decorated function
will be called with one argument being, `message`

.. note::

    You are not required to pass an event into the ``on`` decorator.
    Instead if no event is passed it will take the name from the function being decorated.

2. Multiple event callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^
A single event may have multiple callbacks registered to it. This does require you to pass an
event into the decorator.

.. code-block:: python3

    import lefi

    client = lefi.Client("TOKEN")

    @client.on("message_create")
    async def first_listener(message: lefi.Message) -> None:
        print(f"I got a message from {message.author.username}")

    @client.on("message_create")
    async def second_listener(message: lefi.Message) -> None:
        print(f"I got {message.content}")

    client.run()

3. Overwriting event callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
What if I wanted to overwrite all previous event callbacks?
Fear not, :meth:`.Client.on` has an `overwrite` keyword-argument.

.. code-block:: python3

   import lefi

   client = lefi.Client("TOKEN")

   @client.on("message_create", overwrite=True)
   async def on_message(message: lefi.Message) -> None:
       print(f"Got {message.content}")

.. note::

   This was added to allow for lower level control over events.

4. One time event callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Hey thats pretty cool, but what if I wanted an event callback to run once?
You can use :meth:`.Client.once`! This sets special event callback which will
only run once in the client's lifetime.

.. code-block:: python3

   import lefi

   client = lefi.Client("TOKEN")

   @client.once("ready")
   async def on_ready(user: lefi.User) -> None:
       print(f"Logged into {user.username}")

.. note::

   One time events take precedence over regular events.

And that's all the basics for now. I suggest checking out :ref:`api-reference`
Good luck with the coding!
