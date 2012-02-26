'''
Created on Feb 25, 2012

@author: rcs
'''
import exceptions
import sys
import errno

from pox.core import core
from pox.lib.recoco import *
from pox.lib.util import assert_type

class IOWorker(Task):
  """
  recoco thread for communication between a switch_impl and a controllers
  """
  # TODO: this is highly redundant with of_01.Task... need to refactor Select functionality
  _select_timeout = 5

  def __init__ (self, socket):
    Task.__init__(self)
    self.socket = socket
    # list of (potentially partial) messages to send
    self.write_buf = []
    # We only buffer a single read message at a time
    self.read_buf = ""

    core.addListener(pox.core.GoingUpEvent, self._handle_GoingUpEvent)

  def _handle_GoingUpEvent (self, event):
    self.start()

  def fileno (self):
    return self.controller_sock.fileno()

  def send(self, data):
    assert_type("data", data, [bytes], none_ok=False)
    self.write_buf.append(data)

  def _try_disconnect(self, con):
    ''' helper method '''
    try:
      con.disconnect(True)
    except:
      pass

  def run (self):
    con = None
    while core.running:
      try:
        while True:
          read_sockets = [self.socket]
          exception_sockets = [self.socket]
          write_sockets = []
          if len(self.write_buf) > 0:
            write_sockets.append(self.socket)

          # NOTE: this is not a conventional
          rlist, wlist, elist = yield Select(read_sockets, write_sockets,
                  exception_sockets, self._select_timeout)

          for con in elist:
            self._try_disconnect(con, self.socket)

          for con in rlist:
            try:
              d = self.socket.recv(2048)
              self.read_buf += d
              l = len(self.read_buf)
              while l > 4:
                packet_length = ord(self.read_buf[2]) << 8 | ord(self.read_buf[3])
                if packet_length > l:
                  break
                else:
                  self.read_handler(self.read_buf[0:packet_length])
                  # Will set to '' if there is no more data
                  self.read_buf = self.read_buf[packet_length:]
            except socket.error as (errno, strerror):
              con.msg("Socket error: " + strerror)
              con.disconnect()

          for con in wlist:
            data = self.write_buf.pop(0)
            try:
              l = con.sock.send(data)
              if l != len(data):
                data = data[l:]
                self.write_buf.insert(0,data)
                break
            except socket.error as (errno, strerror):
              if errno != errno.EAGAIN:
                con.msg("Socket error: " + strerror)
                con.disconnect()
      except exceptions.KeyboardInterrupt:
        break
