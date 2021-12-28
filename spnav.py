'''spnav: a ctypes wrapper for libspnav, a Space Navigator 3D mouse client'''

'''
Copyright (c) 2011, Stanley Seibert
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * The names of its contributors may not be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

'''
sjkillen: [2021] X11 bindings removed due to their incompatibility with Python 3.X
'''

from ctypes import cdll, c_int, c_uint, c_void_p, pointer, \
    Structure, Union

libspnav = cdll.LoadLibrary('libspnav.so')

SPNAV_EVENT_ANY = 0
SPNAV_EVENT_MOTION = 1
SPNAV_EVENT_BUTTON = 2

### Python event classes

class SpnavEvent(object):
    '''Space Navigator Event Base class
    
      `ev_type`: **int**
         Type of events.  Either ``SPANV_EVENT_MOTION`` or 
         ``SPNAV_EVENT_BUTTON``.
    '''
    def __init__(self, ev_type):
        self.ev_type = ev_type

class SpnavMotionEvent(SpnavEvent):
    '''Space Navigator Motion Event class
    
      `translation`: 3-tuple of ints
        Translation force X,Y,Z in arbitrary integer units
      `rotation`: 3-tuple of ints
        Rotation torque around axes in arbitrary integer units
      `period`: **int**
        Corresponds to spnav_event_motion.period in libspnav.
        No idea what the meaning of the field is.
    '''
    def __init__(self, translation, rotation, period):
        SpnavEvent.__init__(self, SPNAV_EVENT_MOTION)
        self.translation = tuple(translation)
        self.rotation = tuple(rotation)
        self.period = period

    def __str__(self):
        return 'SPNAV_EVENT_MOTION trans(%d,%d,%d) rot(%d,%d,%d)' \
            % (self.translation + self.rotation)

class SpnavButtonEvent(SpnavEvent):
    '''Space Navigator Button Event class

    Button events are generated when a button on the controller
    is pressed and when it is released.
    
      `bnum`: **int**
        Button number
      `press`: **bool**
        If True, button pressed down, else button released.
    '''
    def __init__(self, bnum, press):
        SpnavEvent.__init__(self, SPNAV_EVENT_BUTTON)
        self.bnum = bnum
        self.press = press

    def __str__(self):
        if self.press:
            state = 'down'
        else:
            state = 'up'
        return 'SPNAV_EVENT_BUTTON %d %s' % (self.bnum, state)


### ctypes C struct wrappers

class spnav_event_motion(Structure):
    '''Space Navigator motion event C struct

    A motion event is produced whenever a force is applied to the 3D mouse.

      `type`: **c_int**
        Always set to SPNAV_EVENT_MOTION

      `x`, `y`, `z`: **c_int**
        Linear translation force.  Sign of value indicates direction.

      `rx`, `ry`, `rz`: **c_int**
        Rotation force around each axis.  Sign of value indicates direction.

      `period`: **c_uint**
        No idea what this is.

      `data`: **c_void_p**
        Raw event data.  Ignore this field.
    '''
    _fields_ = [('type', c_int),
                ('x', c_int),
                ('y', c_int),
                ('z', c_int),
                ('rx', c_int),
                ('ry', c_int),
                ('rz', c_int),
                ('period', c_uint),
                ('data', c_void_p)]

class spnav_event_button(Structure):
    '''Space Navigator button event C struct

    A button event is produced whenever a button on the 3D mouse is pressed
    or released.

      `type`: **c_int**
        Always set to SPNAV_EVENT_BUTTON

      `press`: **c_int**
        Set to 1 when the button is pressed and 0 when released.

      `bnum`: **c_int**
        Button number on device.
    '''
    _fields_ = [('type', c_int),
                ('press', c_int),
                ('bnum', c_int)]

class spnav_event(Union):
    '''Space Navigator Event

    A C union between the motion and button event structs.

      `type`: **c_int**
        SPNAV_EVENT_MOTION or SPNAV_EVENT_BUTTON
      
      `motion`: spnav_event_motion,
        If `type` == ``SPNAV_EVENT_MOTION``, then this
        is a motion event C struct.

      `button`: spnave_event_button,
        If `type` == ``SPNAV_EVENT_BUTTON``, then this
        is a motion event C struct.
    '''
    _fields_ = [('type', c_int),
                ('motion', spnav_event_motion),
                ('button', spnav_event_button) ]

def convert_spnav_event(c_event):
    '''Convert an instance of the spnav_event C union to a pure Python
    instance of SpnavMotionEvent or SpnavButtonEvent.'''
    if c_event.type == SPNAV_EVENT_MOTION:
        motion = c_event.motion
        return SpnavMotionEvent(translation=(motion.x, motion.y, motion.z),
                                rotation=(motion.rx, motion.ry, motion.rz),
                                period=motion.period)
    elif c_event.type == SPNAV_EVENT_BUTTON:
        button = c_event.button
        return SpnavButtonEvent(bnum=button.bnum, press=bool(button.press))
    else:
        raise SpnavException('Invalid spnav event type: %d' % c_event.type)

class SpnavException(Exception):
    '''Base class for all ``spnav`` exceptions.'''
    def __init__(self, msg):
        Exception.__init__(self, msg)

class SpnavConnectionException(SpnavException):
    '''Exception caused by failure to connect to source of spnav events.'''
    def __init__(self, msg):
        SpnavException.__init__(self, msg)

class SpnavWaitException(SpnavException):
    '''Exception caused by error while waiting for spnav event to arrive.'''
    def __init__(self, msg):
        SpnavException.__init__(self, msg)
    
def spnav_open():
    '''Open connection to the daemon via AF_UNIX socket.

    The unix domain socket interface is an alternative to the original
    magellan protocol, and it is *NOT* compatible with the 3D
    connexion driver. If you wish to remain compatible, use the X11
    protocol (spnav_x11_open, see below).

    Raises ``SpnavConnectionException`` if conn
    ection cannot be established.
    '''
    if libspnav.spnav_open() == -1:
        raise SpnavConnectionException(
            'failed to connect to the space navigator daemon')

def spnav_fd():
    '''Retrieves the file descriptor used for communication with the
    daemon, for use with select() by the application, if so required.
    If the X11 mode is used, the socket used to communicate with the X
    server is returned, so the result of this function is always
    reliable.  If AF_UNIX mode is used, the fd of the socket is
    returned or -1 if no connection is open / failure occured.'''
    return libspnav.spnav_fd()

def spnav_close():
    '''Closes connection to the daemon.'''
    libspnav.spnav_close()

def spnav_wait_event():
    '''Blocks waiting for Space Navigator events.

       Note that the block happens inside the libspnav library, so you
       will not be able to interrupt this function with Ctrl-C.  It is
       almost always better to use ``spnav_poll_event()`` instead.

       Returns: An instance of ``SpnavMotionEvent`` or
       ``SpnavButtonEvent``.
    '''
    event = spnav_event()
    ret = libspnav.spnav_wait_event(pointer(event))
    if ret:
        return convert_spnav_event(event)
    else:
        raise SpnavWaitException('zero return code from spnav_wait_event()')

def spnav_poll_event():
    '''Polls for waiting for Space Navigator events.

       Returns: None if no waiting events, otherwise an instance of
       ``SpnavMotionEvent`` or ``SpnavButtonEvent``.
    '''
    event = spnav_event()
    ret = libspnav.spnav_poll_event(pointer(event))
    if ret == 0:
        return None
    else:
        return convert_spnav_event(event)

def spnav_remove_events(event_type):
    '''Removes pending Space Navigator events from the queue.

      This function is useful to purge old events that may have
      queued up after a long calculation.  It helps to keep
      your application appearing more responsive.

      `event_type`: **int**
        The type of events to remove.  ``SPNAV_EVENT_MOTION`` or
        ``SPNAV_EVENT_BUTTON`` removes just motion or button events,
        respectively.  ``SPNAV_EVENT_ANY`` removes both types of events.
    '''
    return libspnav.spnav_remove_events(event_type)
