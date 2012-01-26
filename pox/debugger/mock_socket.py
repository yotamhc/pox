"""
This module provides a MockSocket that can be used to fake TCP connections inside of the simulator
"""

class MockSocket:
  """
      A mock socket that works on a sending and a receiving message channel. Use
      MockSocket.pair() to get a pair of connected MockSockets

      TODO: model failure modes
  """
  def __init__(self, receiving, sending):
    self.receiving = receiving
    self.sending = sending

  def send(self, data):
    """ Send data out on this socket. Data will be available for reading at the receiving
        socket pair. Note that this currently always succeeds and never blocks (unlimited
        receive buffer size)
    """
    return self.sending.send(data)

  def recv(self):
    """ receive data on this sockect. If no data is available to be received, return "".
        NOTE that this is non-standard socket behavior and should be changed to mimic either
        blocking on non-blocking socket semantics
    """
    return self.receiving.recv()

  def set_on_ready_to_recv(self, on_ready):
    """ set a handler function on_ready(socket, size) to be called when data is available
    for reading at this socket """
    self.receiving.on_data = lambda channel, size: on_ready(self, size)

  def ready_to_recv(self):
    return not self.receiving.is_empty()

  def ready_to_send(self):
    return self.sending.is_full()

  def shutdown(self, sig=None):
    """ shutdown a socket. Currently a no-op on this MockSocket object. 
        TODO: implement more realistic closing semantics
    """
    pass

  def close(self):
    """ close a socket. Currently a no-op on this MockSocket object. 
        TODO: implement more realistic closing semantics
    """
    pass

  def fileno(self):
    """ return the pseudo-fileno of this Mock Socket. Currently always returns -1.
        TODO: assign unique pseudo-filenos to mock sockets, so apps don't get confused.
    """
    return -1

  @classmethod
  def pair(cls):
    """ Return a pair of connected sockets """
    a_to_b = MessageChannel()
    b_to_a = MessageChannel()
    a = cls(a_to_b, b_to_a)
    b = cls(b_to_a, a_to_b)
    return (a,b)

class MessageChannel(object):
  """ A undirectional reliable in order byte stream message channel (think TCP half-connection)
  """
  def __init__(self):
    # Single element queue
    self.buffer = ""
    self.on_data = None

  def send(self, msg):
    self.buffer += msg
    if(self.on_data):
      self.on_data(self, len(self.buffer))

    return len(msg)

  def recv(self):
    """ retrieve and return the data stored in this channel's buffer. If buffer is empty, return "" """
    msg = self.buffer
    self.buffer = ""
    return msg

  def is_empty(self):
    return len(self.buffer) == 0

  def is_full(self):
    #  buffer length not constrained currently
    return False

  def __len__(self):
    return len(self.buffer)
