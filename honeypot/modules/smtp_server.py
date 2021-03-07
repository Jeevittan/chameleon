__G__ = "(G)bd249ce4"

from warnings import filterwarnings
filterwarnings(action='ignore',module='.*OpenSSL.*')

from smtpd import SMTPChannel, SMTPServer
from asyncore import loop
from base64 import decodestring
from multiprocessing import Process
from psutil import process_iter
from signal import SIGTERM
from time import sleep
from smtplib import SMTP
from logging import DEBUG, basicConfig, getLogger

class QSMTPServer():
	def __init__(self,ip=None,port=None,username=None,password=None,mocking=False,logs=None):
		self.ip= ip or '0.0.0.0'
		self.port = port or 25
		self.username = username or "test"
		self.password = password or "test"
		self.mocking = mocking or ''
		self.random_servers = []
		self.setup_logger(logs)

	def setup_logger(self,logs):
		self.logs = getLogger("chameleonlogger")
		self.logs.setLevel(DEBUG)
		if logs:
			from custom_logging import CustomHandler
			self.logs.addHandler(CustomHandler(logs))
		else:
			basicConfig()

	def smtp_server_main(self):
		_q_s = self

		class CustomSMTPChannel(SMTPChannel):
			def smtp_EHLO(self, arg):
				if not arg:
					self.push('501 Syntax: HELO hostname')
				if self._SMTPChannel__greeting:
					self.push('503 Duplicate HELO/EHLO')
				else:
					self._SMTPChannel__greeting = arg
					self.push('250-{0} Hello {1}'.format(self._SMTPChannel__fqdn, arg))
					self.push('250-8BITMIME')
					self.push('250-AUTH LOGIN PLAIN')
					self.push('250 STARTTLS')

			def smtp_AUTH(self, arg):
				try:
					if arg.startswith('PLAIN '):
						_, username, password = decodestring(arg.split(' ')[1].strip().encode("utf-8")).split('\0')
						if username ==  _q_s.username and password == _q_s.password:
							_q_s.logs.info(["servers",{'server':'smtp_server','action':'login','status':'success','ip':self.addr[0],'port':self.addr[1],'username':_q_s.username,'password':_q_s.password}])
						else:
							_q_s.logs.info(["servers",{'server':'smtp_server','action':'login','status':'faild','ip':self.addr[0],'port':self.addr[1],'username':username,'password':password}])
				except Exception as e:
					_q_s.logs.error(["errors",{'server':'smtp_server','error':'smtp_AUTH',"type":"error -> "+repr(e)}])

				self.push('235 Authentication successful')

			def __getattr__(self, name):
				self.smtp_QUIT(0)

		class CustomSMTPServer(SMTPServer):
			def __init__(self, localaddr, remoteaddr):
				SMTPServer.__init__(self, localaddr, remoteaddr)

			def process_message(self, peer, mailfrom, rcpttos, data,mail_options=None,rcpt_options=None):
				return

			def handle_accept(self):
				conn, addr = self.accept()
				CustomSMTPChannel(self, conn, addr)

		CustomSMTPServer((self.ip, self.port), None)
		loop(timeout=1.1,use_poll= True)

	def run_server(self,process=False):
		self.close_port()
		if process:
			self.smtp_server = Process(name='QSMTPServer_', target=self.smtp_server_main)
			self.smtp_server.start()
		else:
			self.smtp_server_main()

	def kill_server(self,process=False):
		self.close_port()
		if process:
			self.smtp_server.terminate()
			self.smtp_server.join()

	def test_server(self,ip,port,username,password):
		try:
			sleep(2)
			_ip = ip or self.ip
			_port = port or self.port 
			_username = username or self.username
			_password = password or self.password
			s = SMTP(_ip,_port)
			s.ehlo()
			s.login(_username,_password)
			s.sendmail("fromtest","totest","Nothing")
			s.quit()
		except Exception:
			pass

	def close_port(self):
		for process in process_iter():
			try:
				for conn in process.connections(kind='inet'):
					if self.port == conn.laddr.port:
						process.send_signal(SIGTERM)
						process.kill()
			except:
				pass

if __name__ == "__main__":
	from server_options import server_arguments
	parsed = server_arguments()

	if parsed.docker or parsed.aws or parsed.custom:
		qsmtpserver = QSMTPServer(ip=parsed.ip,port=parsed.port,username=parsed.username,password=parsed.password,mocking=parsed.mocking,logs=parsed.logs)
		qsmtpserver.run_server()

	if parsed.test:
		qsmtpserver = QSMTPServer(ip=parsed.ip,port=parsed.port,username=parsed.username,password=parsed.password,mocking=parsed.mocking,logs=parsed.logs)
		qsmtpserver.test_server(ip=parsed.ip,port=parsed.port,username=parsed.username,password=parsed.password)
