#! /usr/bin/python

import os, time, math
import threading, Queue
import zmq



class communicationSocket:
	
	def __init__(self, port, ip=None, queueCommands=None, queueStatus=None):
		
		# Internalise parameters.
		self.queueCommands = queueCommands
		self.queueStatus = queueStatus
		
		# Set up timeout variables.
		self.rasPiConnected = True
		self.rasPiConnectionTimeout  = 10
		
		# Create the context.
		self.context = zmq.Context()
		# Create socket.
		self.socket = self.context.socket(zmq.PAIR)
		# Use * interface for server, ip for client!
		if ip==None:
			ip = "*"
			self.socket.bind("tcp://"+str(ip)+":"+str(port))
		else:
			self.socket.connect("tcp://"+str(ip)+":"+str(port))
		print "Connected to communication socket on tcp://"+str(ip)+":"+str(port) + "."
		# Get the sockets file descriptor for setting up a gtk IO watch.
		self.fileDescriptor = self.socket.getsockopt(zmq.FD)
		
		
	
	def reset(self, ip, port):
		del self.socket
		self.socket = self.context.socket(zmq.PAIR)
		self.socket.connect("tcp://"+str(ip)+":"+str(port))
		print "Connecting to communication socket on tcp://"+str(ip)+":"+str(port) + "."
	
	
	# Send function.
	def sendMulti(self, command, string):
		self.socket.send_multipart([command, string])  
		print "Sent " + command + ", " + string + "."

	

	# Register this as a gobject IO watch that fires on changes of the file descriptor.
	def callbackIOActivity(self, fd, condition, socket):
		# Keep running as long as something waits in the socket.
		while self.socket.getsockopt(zmq.EVENTS) & zmq.POLLIN:

			# Retrieve the message from the socket.
			msg = self.socket.recv_multipart()
			
			# Extract message type and message data.
			messageType, message = msg
			
			print "Received: " + messageType + ", " + message

			# If message is status info...
			if messageType == "command":
				# ... forward to command status queue.
				if self.queueCommands != None:
					self.queueCommands.put(message)
					print "Command " + message + " put into queue."
			# If message is status info...
			if messageType == "status":
				# ... forward it to the status queue.
				if self.queueStatus != None:
					self.queueStatus.put(message)
			# If message is error...
			elif messageType == "error":
				#TODO handle the errors...
				pass
			# If message is a returning ping...
			elif messageType == "ping":
				# ... set connected flag and reset the ping counter. 
				self.rasPiConnected = True
				self.rasPiConnectionTimeout  = 10

		# Return true, otherwise function will be removed from IO watch.		
		return True
		
	
	# This should run every second as a gobject timeout function, but only from PC.
	def countdownRasPiConnection(self):
		if self.rasPiConnectionTimeout  > 0:
			self.rasPiConnectionTimeout  -= 1
		if self.rasPiConnectionTimeout  < 1:
			self.rasPiConnected = False
		return True
	
	
	# This should run ever 500 ms as gobject timeout function, but only from PC.
	def pollRasPiConnection(self):
		# Send a ping.
		command = "ping"
		path = ""
		self.socket.send_multipart([command, path])
		# The receive function is running elsewhere and
		# will reset the timeout counter on a returning ping.
		return True
		


class fileSender(threading.Thread):

	def __init__(self, ip, port, queueStatusIn, queueStatusOut):
		
		self.PIPELINE = 5 # Chunks.
		self.chunksSent = 0
		self.queueStatusIn = queueStatusIn
		self.queueStatusOut = queueStatusOut
		self.stopThread = threading.Event()
		
		# Create context.
		context = zmq.Context()

		# Create the router.
		# Upon reception, a router prepends the the identity of the 
		# sender to the message.
		# Overflowing packets will be dropped.
		self.router = context.socket(zmq.ROUTER)
		# Set high water mark.
		self.socket_set_hwm(self.router, self.PIPELINE)
		clientPath = "tcp://" + str(ip) + ":" + str(port)
		if not self.queueStatusOut.qsize():
			self.queueStatusOut.put("Connecting file transmission server to " + clientPath + ".")
		print "Connecting file transmission server to " + clientPath + "."
		self.router.connect(clientPath)
		
		# Set up poll on socket events.
		# This is used to avoid the blocking receive function.
		self.poller = zmq.Poller()
		self.poller.register(self.router, zmq.POLLIN)
		
		
		# Call super class init function.
		super(fileSender, self).__init__()

	
	def reset(self, ip, port):
		clientPath = "tcp://" + str(ip) + ":" + str(port)
		print "Listening on tcp://" + str(ip) + ":" + str(port)
		self.router.connect(clientPath)
	
	# This will run right after init function.
	def run(self):
		print "File transmission server running.\n"
		while not self.stopThread.isSet():
			# Poll for receive events.
			socketsWithEvents = dict(self.poller.poll(1))	# Timeout 1 ms.
			if self.router in socketsWithEvents and socketsWithEvents[self.router] == zmq.POLLIN:
				# Receive a multi frame message.
				# First frame in each message is the sender identity.
				# Second frame is "fetch" command.
				# Third is chunk offset.
				# Fourth is chunk size.
				try:
					# Get the message.
					msg = self.router.recv_multipart(zmq.DONTWAIT)
				#	print msg
				except zmq.ZMQError as e:
					if e.errno == zmq.ETERM:
						print "finished..?"
						#return   # shutting down, quit
					else:
						raise

				# Get the transfert meta data out of the first message.
				identity, command, offset_str, chunksz_str = msg

				# If this is the first message which states the file, open it.
				if command[:8] == "filename":
					print "Opening file."
					filename = command[9:]
			#		print "Requested file ", filename, "."
					# Open the file to transmit.
					print filename
					file = open(filename, "rb")

					file.seek(0,2)
					fileSize = str(file.tell())
					self.router.send_multipart([identity, fileSize])
					print "bar"
	
				elif command[:4] == "done":
					file.close()
					self.chunksSent = 0
					print "Transmission complete. Idling..."
		
				else:
			#		print "Packet requested from ", offset_str
					# Check if command is "fetch".
					# b in front of string means byte literal in python 3.
					# Will be ignored in python 2.
					assert command == b"fetch"

					# Cast offset and chunk size to integer.
					offset = int(offset_str)
					chunksz = int(chunksz_str)
					time.sleep(0.05)
					file.seek(0,2)
					filePackets = int(math.ceil(file.tell() / float(chunksz)))

					if(self.chunksSent < filePackets):
						# Get the relevant chunk form the file.
						file.seek(offset, os.SEEK_SET)	# Set the offset.
						data = file.read(chunksz)		# Read specified number of bytes at offset.
						# Send resulting chunk to client
						self.router.send_multipart([identity, str(offset), data])
						print "Sending packet ", str(self.chunksSent+1), " of ", filePackets, " from ", str(offset)
						self.chunksSent += 1
					# If transfer complete, reset everything and make ready again.
					else:	# TODO: this is probably never used...
						file.close()
						print "Transmission complete. Idling..."
						#break
						
		
	# Copied from zhelpers.
	# https://github.com/imatix/zguide/blob/master/examples/Python/zhelpers.py
	def socket_set_hwm(self, socket, hwm=-1):
	    """libzmq 2/3/4 compatible sethwm"""
	    try:
		   socket.sndhwm = socket.rcvhwm = hwm
	    except AttributeError:
		   socket.hwm = hwm
	
	def join(self, timeout=None):
		if not self.queueStatusOut.qsize():
			self.queueStatusOut.put("Stopping file transfer server.")
		# Try to stop the thread nicely.
		# Won't work if we are waiting for a message...
		self.stopThread.set()
		# Stop thread the hard way after given timeout.
		threading.Thread.join(self, timeout)
	
	
		

class fileReceiver(threading.Thread):

	def __init__(self, ip, port, queueFileTransferIn, queueFileTransferOut, console=None):
	
		self.CHUNK_SIZE = 25000
		self.PIPELINE = 5
		
		self.queueFileTransferIn = queueFileTransferIn
		self.queueFileTransferOut = queueFileTransferOut
		self.console = console
		#self.filenameTarget = "./currentPrint.mkp"

		# Create the context.
		context = zmq.Context()

		# Create socket.
		self.dealer = context.socket(zmq.DEALER)
		self.socket_set_hwm(self.dealer, self.PIPELINE)
		self.dealer.bind("tcp://"+ip+":"+port)
		
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
			command, filenames = self.queueFileTransferIn.get()
			if command == "get" and not self.receiving:
				filenameSource, filenameTarget = filenames.split(":")
				print "Received filename " + filenameSource + "."
				print "Saving to " + filenameTarget + "."
				self.receiving = True
				self.receiveFile(filenameSource, filenameTarget)
	
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

	def receiveFile(self, filenameSource, filenameTarget):
		print "Starting transmission."
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
		with	open(filenameTarget, "wb") as file:	# CHANGED TO R+B
		
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
			self.console.addLine("Stopping file receiver thread")
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
