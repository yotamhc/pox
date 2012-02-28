'''
Created on Feb 25, 2012

@author: rcs
'''
import exceptions
import sys
import errno
import logging
import Queue
import socket

from pox.lib.util import assert_type, makePinger
from pox.lib.recoco import Select, Task

log = logging.getLogger()

class IOWorker(object):
  """ Generic IOWorker class. Defines the IO contract for our simulator. Fire and forget semantics for send. 
      Received data is being queued until explicitely consumed by the client
  """
  def __init__(self):
    self.send_buf = ""
    self.receive_buf = ""
    self._on_data_receive = lambda worker: None
    
  def set_receive_handler(self, block):
    self._on_data_receive = block

  def send(self, data):
    """ send data from the client side. fire and forget. """
    assert_type("data", data, [bytes], none_ok=False)
    self.send_buf += data

  def push_receive_data(self, new_data):
    """ notify client of new received data. called by a Select loop """
    self.receive_buf += new_data
    self._on_data_receive(self)

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
    self.socket = socket
    self.pinger = pinger

  def fileno(self):
    return self.socket.fileno()

  def send(self, data):
    IOWorker.send(self, data)
    self.pinger.ping()
    
class DeferredIOWorker(object):
  '''
  Wrapper class for RecocoIOWorkers.
  
  Rather than actually sending/receiving right away, queue the messages.
  Then there are separate methods for actually sending the messages via
  the wrapped io_worker
  '''
  def __init__(self, io_worker):
    self.io_worker = io_worker
    # Thread-safe read and write queues of indefinite length
    self.receive_queue = Queue.Queue()
    self.send_queue = Queue.Queue()
  
  def permit_send(self):
    '''
    deque()s the first element of the write queue, and actually sends it
    across the wire.
    
    raises an exception if the write queue is empty
    '''
    message = self.send_queue.get()
    # TODO: will recoco guarentee in-order delivery of a sequence of these send requests?
    # TODO: do I need to ensure thread-safety? We're crossing thread boundaries here...
    self.io_worker.send(message)
    
  def send(self, data):
    """ send data from the client side. fire and forget. """
    self.send_queue.put(data)
    
  def has_pending_sends(self):
    ''' called by the "arbitrator" in charge of deferal '''
    return not self.send_queue.empty()
  
  def permit_receive(self):
    data = self.receive_queue.get()
    self.io_worker.push_receive_data(data)
  
  def push_receive_data(self, new_data):
    ''' called from the Select loop '''
    self.receive_queue.put(new_data)
    
  def has_pending_receives(self):
    ''' called by the "arbitrator" in charge of deferal '''
    return not self.receive_queue.empty()
  
  # Delegation functions.
  # TODO: is there a more pythonic way to implement delegation?
  
  @property
  def ready_to_send(self):
    ''' Called by Select loop to see if we're actually ready to send '''
    # We only push write data onto the worker after we've permitted it.
    return self.io_worker.ready_to_send
  
  def set_receive_handler(self, block):
    self.io_worker.set_receive_handler(block)
  
  def fileno(self):
    return self.io_worker.fileno()
  
  def close(self):
    return self.io_worker.close()
  
  def peek_receive_buf(self):
    return self.io_worker.peek_receive_buf()

  def consume_receive_buf(self, l):
    """ called from the client to consume receive buffer """
    return self.io_worker.consume_receive_buf(l)
  
  def consume_send_buf(self, l):
    return self.io_worker.consume_send_buf(l)
    
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
  
  def create_deferred_worker_for_socket(self, socket):
    real_worker = self.create_worker_for_socket(socket)
    deferred_worker = DeferredIOWorker(real_worker)
    return deferred_worker

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
