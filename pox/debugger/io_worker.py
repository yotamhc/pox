'''
Created on Feb 25, 2012

@author: rcs
'''
import exceptions
import sys
import errno
import logging

from pox.core import core
from pox.lib.recoco import *
from pox.lib.util import assert_type, makePinger

log = logging.getLogger()

class IOWorker(object):
  """ Generic IOWorker class. Defines the IO contract for our simulator. Fire and forget semantics for send. 
      Received data is being queued until explicitely consumed by the client
  """
  def __init__(self):
    self.send_buf = ""
    self.receive_buf = ""
    self.on_data_receive = lambda worker: None

  def send(self, data):
    """ send data from the client side. fire and forget. """
    assert_type("data", data, [bytes], none_ok=False)
    self.send_buf += data

  def push_receive_data(self, new_data):
    """ notify client of new received data. """
    self.receive_buf += new_data
    self.on_data_receive(self)

  def peek_receive_buf(self):
    return self.receive_buf

  def consume_receive_buf(self, l):
    """ called from the client to consume receive buffer """
    assert(len(self.receive_buf) >= l)
    self.receive_buf = self.receive_buf[l:]

  @property
  def ready_to_send(self):
    return len(self.send_buf) > 0

  def consume_send_buf(self, l):
    assert(len(self.send_buf)>=l)
    self.send_buf = self.send_buf[l:]

  def close(self):
    pass

class RecocoIOWorker(IOWorker):
  """ An IOWorker that works with our RecocoIOLoop, and notifies it via pinger """
  def __init__(self, socket, pinger):
    IOWorker.__init__(self)
    # list of (potentially partial) messages to send
    self.socket = socket
    self.pinger = pinger

  def fileno(self):
    return self.socket.fileno

  def send(self, data):
    IOWorker.send(self, data)
    self.pinger.ping()

class RecocoIOLoop(Task):
  """
  recoco task that handles the actual IO for our IO workers
  """
  _select_timeout = 5
  _BUF_SIZE = 8192

  def __init__ (self):
    Task.__init__(self)
    self.workers = set()
    self.pinger = makePinger()

  def create_worker_for_socket(self, socket):
    worker = RecocoIOWorker(socket, self.pinger)
    self.workers.add(worker)
    self.pinger.ping()
    return worker

  def stop(self):
    self.running = False
    self.pinger.ping()

  def run (self):
    self.running = True
    while self.running:
      try:
        read_sockets = list(self.workers) + [ self.pinger ]
        write_sockets = [ worker for worker in self.workers if worker.ready_to_send ]
        exception_sockets = list(self.workers)

        rlist, wlist, elist = yield Select(read_sockets, write_sockets,
                exception_sockets, self._select_timeout)

        if self.pinger in rlist :
          self.pinger.pongAll()
          rlist.remove(self.pinger)

        for worker in elist:
          worker.close()
          self.workers.remove(worker)

        for worker in rlist:
          try:
            data = worker.socket.recv(self._BUF_SIZE)
            worker.push_receive_data(data)
          except socket.error as (errno, strerror):
            log.error("Socket error: " + strerror)
            worker.close()
            self.workers.remove(worker)

        for worker in wlist:
          try:
            l = worker.socket.send(worker.send_buf)
            if l > 0:
              worker.consume_send_buf(l)
          except socket.error as (errno, strerror):
            if errno != errno.EAGAIN:
              log.error("Socket error: " + strerror)
              worker.close()
              self.workers.remove(worker)

      except exceptions.KeyboardInterrupt:
        break
