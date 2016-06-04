#! /usr/bin/python

import os, time, math
import threading, Queue
import zmq



class communicationSocket(threading.Thread):
	
	def __init__(self, port, ip=None):
		
		# Create the context.
		context = zmq.Context()
		
		# Create socket.
		self.socket = context.socket(zmq.PAIR)
		if ip==None:
			ip = "*"
		self.socket.connect("tcp://"+ip+":"+port)
		
		
		
		


class fileSender(threading.Thread):

	def __init__(self, port):
		pass	#TODO
		

class fileReceiver(threading.Thread):

	def __init__(self, ip, port, queueFileTransferIn, queueFileTransferOut):
	
		self.CHUNK_SIZE = 25000
		self.PIPELINE = 5
		
		self.queueFileTransferIn = queueFileTransferIn
		self.queueFileTransferOut = queueFileTransferOut
		self.filenameTarget = "./currentPrint.mkp"

		# Create the context.
		context = zmq.Context()

		# Create socket.
		self.dealer = context.socket(zmq.DEALER)
		self.socket_set_hwm(self.dealer, self.PIPELINE)
		self.dealer.connect("tcp://"+ip+":"+port)
		
		# Thread stop event.
		self.stopThread = threading.Event()
		
		self.receiving = False
		
		# Call super class init function.
		super(fileReceiver, self).__init__()
	
	
	# This will run right after init function.
	def run(self):
		# Go straight into idle mode.
		print "File transmission thread started.\n"
		self.idle()
	
	# Check for input models in the queue.
	def newInputInQueue(self):
		if self.queueFileTransferIn.qsize():
			print "hurz"
			return True
		else:
			return False


	# Continuously check queue for start signals.
	def idle(self):
		self.status = "idle"
		# Do nothing as long as nothing is in the queue.
		while not self.newInputInQueue() and not self.stopThread.isSet():
			time.sleep(0.1)
		# If input has arrived get the input run slicer function.
		if not self.stopThread.isSet():
			command, filenameSource = self.queueFileTransferIn.get()
			if command == "get" and not self.receiving:
				print "Received filename " + filenameSource + "."
				print "Starting transmission."
				self.receiving = True
				self.receiveFile(filenameSource)
	
	'''
	def runTransmission(self, file):
		# Don't run if stop condition is set.
		while not self.stopThread.isSet():
			# Check if new input is in queue. If not...
			if not self.newInputInQueue():
				# ...do the slicing.
				self.sliceStack = self.updateSlices(inputModel)
			# If yes...
			else:
				# Break the loop, return to idle mode and restart from there.
				break
			# Write the model to the output queue.
			self.queueSlicerOut.put(self.sliceStack)
			break
		# Go back to idle mode.
		self.idle()
	'''	

	def receiveFile(self, filenameSource):
	
		# Set the file transfer credit.
		# At the start we have full credit.
		credit = self.PIPELINE   # Up to PIPELINE chunks in transit.
		
		# Define file chunk counters. 
		offsetReq = 0		# Requested file address.
		total = 0			# Total bytes received
		chunks = 0		# Total chunks received
		fileSeek = 0		# Current position in file.	
		requestList = []	# List of addresses that are currently requested.
		'''
		# Create a file to write to.
		# First, open it with write tag to empty it.
		try:
			file = open(filenameTarget, "wb")
		except IOError:
			print "File not found."
		file.close()
		'''
		# Then, open the emptied file again with append tag.
		with	open(self.filenameTarget, "wb") as file:	# CHANGED TO R+B
		
			# Send the name of the requested file to server.
			self.dealer.send_multipart([
						b"filename "+ filenameSource,
						b"%i" % offsetReq,
						b"%i" % self.CHUNK_SIZE,
					])

			# Retrieve the file size from server.
			# Blocking receive.
			fileSize = self.dealer.recv()
			fileSize = int(fileSize)
			print "File size: ", fileSize, "bytes."

	
			transmissionFinished = True
			while not self.stopThread.isSet():
				# Ask for file chunks as long as we have credits...
				while credit:
					# b in front of string means byte literal in python 3.
					# Will be ignored in python 2.
					if offsetReq < fileSize:
						self.dealer.send_multipart([
							b"fetch",
							b"%i" % offsetReq,
							b"%i" % self.CHUNK_SIZE,
						])
#						print "Requesting chunk ", str(offsetReq)
						requestList.append(offsetReq)

						offsetReq += self.CHUNK_SIZE
						credit -= 1
					else:
						break

				# Receive next chunk.
				try:
					# Blocking receive.
					msg = self.dealer.recv_multipart()
					address, chunk = msg
					address = int(address)
					if address in requestList:
						print "Received chunk ", str(chunks+1), " for address ", str(address)
						requestList = [x for x in requestList if x != address]
					else:
						print "Received non requested chunk. Dropping..."
						chunk = None
				except zmq.ZMQError as e:
					if e.errno == zmq.ETERM:
						print "Context was terminated."#	return   # shutting down, quit
					else:
						raise

				if chunk != None:
					# Write chunk to file at offset.
					file.seek(address, os.SEEK_SET)	# Set the offset.
					file.write(chunk)				# Write chunk at offset.
		

					# Keep track of received chunks.
					chunks += 1
					credit += 1
					size = len(chunk)
					total += size
		
					# If all packets requested, send end command.
					if len (requestList) == 0:
						transmissionFinished = True
						self.dealer.send_multipart([
							b"done ",
							b"%i" % offsetReq,
							b"%i" % self.CHUNK_SIZE,
							])
					#	print "foo"
						break
					
					
					# Check the queue for commands.
					if self.newInputInQueue():
						msg = self.queueFileTransferIn.get()
						command, filenameSource = msg
						if command == "stop":
							self.receiving = False
							transmissionFinished == False
							print "Transmission cancelled."
							break

			file.close()
			if transmissionFinished:
				print "Transmission completed, %i bytes received." %total
				self.queueFileTransferOut.put("success")
			else:
				print "Transmission cancelled."
				self.queueFileTransferOut.put("fail")
			
			time.sleep(1) # Give main thread a chance to empty queue.
			self.receiving = False
			self.idle()
			#dealer.close()
			

	
	def stopTransmission(self):
		self.stopTrans.set()
		
	
	def stop(self):
		if self.console != None:
			self.console.addLine("Stopping slicer thread")
		self.stopThread.set()
	
	def join(self, timeout=None):
		if self.console != None:
			self.console.addLine("Stopping slicer thread")
		self.stopThread.set()
		threading.Thread.join(self, timeout)

	
	
	# Copied from zhelpers.
	# https://github.com/imatix/zguide/blob/master/examples/Python/zhelpers.py
	def socket_set_hwm(self, socket, hwm=-1):
	    """libzmq 2/3/4 compatible sethwm"""
	    try:
		   socket.sndhwm = socket.rcvhwm = hwm
	    except AttributeError:
		   socket.hwm = hwm

'''
class fileSender:

	def __init__(self, port):


	def sendFile(self, filenameTarget, filenameSource):
	
	
	def stopTransmission(self):
	
	
	def closeSocket(self):
	
	
	# Copied from zhelpers.
	# https://github.com/imatix/zguide/blob/master/examples/Python/zhelpers.py
	def socket_set_hwm(socket, hwm=-1):
	    """libzmq 2/3/4 compatible sethwm"""
	    try:
		   socket.sndhwm = socket.rcvhwm = hwm
	    except AttributeError:
		   socket.hwm = hwm
'''
