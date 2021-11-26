.. currentmodule:: lefi

API-Reference
=============
The public API-Reference of the wrapper. This shows all public
methods and classes. To see internal methods and classes refer to :doc:`Internal API-Reference <Internal-API-Reference>`

Version
-------
.. data:: __version__

    The currrent version of the wrapper is |release|.

    .. note::

        This is based off semantic versioning.

Client
------
.. autoclass:: Client
    :exclude-members: application_command, on, once
    :members:

    .. autodecorator:: lefi.Client.application_command

    .. autodecorator:: lefi.Client.on

    .. autodecorator:: lefi.Client.once

Event reference
---------------
All events that the client can use.

.. function:: interaction_create(interaction)

    Dispatched when an interaction is created by a user.

    :param interaction: The created interaction
    :type interaction: :class:`.Interaction`

.. function:: ready(user)

   Dispatched when the client is ready.

   :param user: The client's current user
   :type user: :class:`.User`

.. function:: guild_create(guild)

   Dispatched when the client joins a new guild or when connecting.

   :param guild: The guild instance which is currently relevant
   :type guild: :class:`.Guild`

.. function:: guild_update(before, after)

   Dispatched when a guild is updated.

   :param before: The guild before being updated
   :type before: :class:`.Guild`

   :param after: The guild after being updated
   :type after: :class:`.Guild`

.. function:: guild_delete(guild)

   Dispatched when the client is removed from a guild.

   :param guild: The guild which was deleted
   :type guild: :class:`.Guild`

.. function:: message_create(message)

   Dispatched when a message is sent.

   :param message: The message which was sent
   :type message: :class:`.Message`

.. function:: message_delete(message)

   Dispatched when a message is deleted.

   :param message: The message which was deleted
   :type message: Union[:class:`.Message`, :class:`.DeletedMessage`]

.. function:: message_update(before, after)

   Dispatched when a message is editted.

   :param before: The message before being editted
   :type before: :class:`.Message`

   :param after: The message after being editted
   :type after: :class:`.Message`

.. function:: channel_create(channel)

   Dispatched when a channel is created.

   :param channel: The just now created channel
   :type channel: Union[:class:`.CategoryChannel`, :class:`.TextChannel`, :class:`VoiceChannel`]

.. function:: channel_update(before, after)

   Dispatched when a channel is editted.

   :param before: The channel before being editted
   :type before: Union[:class:`.CategoryChannel`, :class:`.TextChannel`, :class:`VoiceChannel`]

   :param after: The channel after being editted
   :type after: Union[:class:`.CategoryChannel`, :class:`.TextChannel`, :class:`VoiceChannel`]

.. function:: channel_delete(channel)

   Dispatched when a channel is deleted.

   :param channel: The channel that got deleted
   :type channel: Union[:class:`.CategoryChannel`, :class:`.TextChannel`, :class:`VoiceChannel`]

.. function:: voice_state_update(before, after)

   Dispatched when a voice state is updated.

   :param before: The voice state before being editted
   :type before: :class:`.VoiceState`

   :param after: The voice state after being editted
   :type after: :class:`.VoicState`

.. function:: thread_create(thread)

   Dispatched when a thread is created.

   :param thread: The just now created thread
   :type thread: :class:`.Thread`

.. function:: thread_update(before, after)

   Dispatched when a thread is editted.

   :param before: The thread before being editted
   :type before: :class:`.Thread`

   :param after: The thread after being editted
   :type after: :class:`.Thread`

.. function:: thread_delete(thread)

   Dispatched when a thread is deleted.

   :param thread: The thread which was deleted
   :type thread: :class:`.Thread`

.. function:: thread_member_add(member)

   Dispatched when a new member is added to a thread.

   :param member: The member which was added
   :type member: :class:`.ThreadMember`

.. function:: thread_member_remove(member)

   Dispatched when a member is removed from a thread.

   :param member: The member which was removed
   :type member: :class:`.ThreadMember`

Base models
-----------
Base models which some models extend.

Messageable
~~~~~~~~~~~
.. autoclass:: lefi.base.Messageable
    :members:

BaseTextChannel
~~~~~~~~~~~~~~~
.. autoclass:: lefi.base.BaseTextChannel
    :members:

Discord models
--------------
Models which represent discord objects.

.. danger::

   Users shouldn't be constructing these classes.

TextChannel
~~~~~~~~~~~
.. autoclass:: TextChannel
    :inherited-members:
    :members:

VoiceChannel
~~~~~~~~~~~~
.. autoclass:: VoiceChannel
    :inherited-members:
    :members:

CategoryChannel
~~~~~~~~~~~~~~~
.. autoclass:: CategoryChannel
    :inherited-members:
    :members:

DMChannel
~~~~~~~~~
.. autoclass:: DMChannel
    :inherited-members:
    :members:

Attachment
~~~~~~~~~~
.. autoclass:: Attachment
    :inherited-members:
    :members:

CDN Asset
~~~~~~~~~
.. autoclass:: CDNAsset
    :inherited-members:
    :members:

Embed
~~~~~
.. autoclass:: Embed
    :members:

Exceptions
----------
.. currentmodule:: lefi.errors

Exceptions which the wrapper can raise.

Client errors
~~~~~~~~~~~~~
.. autoexception:: lefi.errors.ClientException
    :exclude-members: __init__, __new__
    :inherited-members:

Voice errors
~~~~~~~~~~~~
.. autoexception:: VoiceException
    :exclude-members: __init__, __new__
    :inherited-members:

.. autoexception:: OpusNotFound
    :exclude-members: __init__, __new__
    :show-inheritance:

HTTP errors
~~~~~~~~~~~
.. autoexception:: HTTPException
    :exclude-members: __init__, __new__
    :show-inheritance:
    :inherited-members:

.. autoexception:: BadRequest
    :exclude-members: __init__, __new__
    :show-inheritance:

.. autoexception:: Forbidden
    :exclude-members: __init__, __new__
    :show-inheritance:

.. autoexception:: NotFound
    :exclude-members: __init__, __new__
    :show-inheritance:

.. autoexception:: Unauthorized
    :exclude-members: __init__, __new__
    :show-inheritance:
