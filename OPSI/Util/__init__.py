#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2006-2016 uib GmbH <info@uib.de>
# http://www.uib.de/

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
General utility functions.

This module holds various utility functions for the work with opsi.
This includes functions for (de)serialisation, converting classes from
or to JSON, working with librsync and more.

:copyright:	uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import codecs
import json
import os
import random
import re
import shutil
import socket
import struct
import time
import types
from contextlib import closing
from Crypto.Cipher import Blowfish
from hashlib import md5
from itertools import islice

try:
	import argparse
except ImportError:
	import _argparse as argparse

from OPSI.Logger import Logger
from OPSI.Types import (forceBool, forceFilename, forceFqdn, forceInt,
						forceIPAddress, forceNetworkAddress, forceUnicode)

__version__ = '4.0.6.41'

logger = Logger()

if os.name == 'posix':
	from duplicity import librsync
elif os.name == 'nt':
	try:
		import librsync
	except Exception as e:
		logger.error(u"Failed to import librsync: %s" % e)

BLOWFISH_IV = 'OPSI1234'
OPSI_GLOBAL_CONF = u'/etc/opsi/global.conf'
RANDOM_DEVICE = u'/dev/urandom'
_ACCEPTED_CHARACTERS = (
	"abcdefghijklmnopqrstuvwxyz"
	"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	"0123456789"
)


class PickleString(str):

	def __getstate__(self):
		return base64.standard_b64encode(self)

	def __setstate__(self, state):
		self = base64.standard_b64decode(state)


def deserialize(obj, preventObjectCreation=False):
	newObj = None
	if not preventObjectCreation and isinstance(obj, dict) and 'type' in obj:
		try:
			import OPSI.Object
			c = eval('OPSI.Object.%s' % obj['type'])
			newObj = c.fromHash(obj)
		except Exception as error:
			logger.debug(u"Failed to get object from dict {0!r}: {1}", obj, forceUnicode(error))
			return obj
	elif isinstance(obj, list):
		newObj = [deserialize(tempObject, preventObjectCreation=preventObjectCreation) for tempObject in obj]
	elif isinstance(obj, dict):
		newObj = {}
		for (key, value) in obj.items():
			newObj[key] = deserialize(value, preventObjectCreation=preventObjectCreation)
	else:
		return obj

	return newObj


def serialize(obj):
	newObj = None
	if isinstance(obj, (unicode, str)):
		return obj
	elif hasattr(obj, 'serialize'):
		newObj = obj.serialize()
	elif isinstance(obj, (list, set, types.GeneratorType)):
		newObj = [serialize(tempObject) for tempObject in obj]
	elif isinstance(obj, dict):
		newObj = {}
		for key, value in obj.items():
			newObj[key] = serialize(value)
	else:
		return obj

	return newObj


def formatFileSize(sizeInBytes):
	if sizeInBytes < 1024:
		return '%i' % sizeInBytes
	elif sizeInBytes < 1048576:  # 1024**2
		return '%iK' % (sizeInBytes / 1024)
	elif sizeInBytes < 1073741824:  # 1024**3
		return '%iM' % (sizeInBytes / 1048576)
	elif sizeInBytes < 1099511627776:  # 1024**4
		return '%iG' % (sizeInBytes / 1073741824)
	else:
		return '%iT' % (sizeInBytes / 1099511627776)


def fromJson(obj, objectType=None, preventObjectCreation=False):
	obj = json.loads(obj)
	if isinstance(obj, dict) and objectType:
		obj['type'] = objectType
	return deserialize(obj, preventObjectCreation=preventObjectCreation)


def toJson(obj, ensureAscii=False):
	return json.dumps(serialize(obj), ensure_ascii=ensureAscii)


def librsyncSignature(filename, base64Encoded=True):
	try:
		with open(filename, 'rb') as f:
			with closing(librsync.SigFile(f)) as sf:
				sig = sf.read()

				if base64Encoded:
					sig = base64.b64encode(sig)

				return sig
	except Exception as e:
		raise Exception(u"Failed to get librsync signature: %s" % forceUnicode(e))


def librsyncPatchFile(oldfile, deltafile, newfile):
	logger.debug(u"Librsync : %s, %s, %s" % (oldfile, deltafile, newfile))
	if oldfile == newfile:
		raise ValueError(u"Oldfile and newfile are the same file")
	if deltafile == newfile:
		raise ValueError(u"deltafile and newfile are the same file")
	if deltafile == oldfile:
		raise ValueError(u"oldfile and deltafile are the same file")

	bufsize = 1024 * 1024
	try:
		with open(oldfile, "rb") as of:
			with open(deltafile, "rb") as df:
				with open(newfile, "wb") as nf:
					with closing(librsync.PatchedFile(of, df)) as pf:
						data = True
						while data:
							data = pf.read(bufsize)
							nf.write(data)
	except Exception as e:
		raise Exception(u"Failed to patch file: %s" % forceUnicode(e))


def librsyncDeltaFile(filename, signature, deltafile):
	bufsize = 1024 * 1024
	try:
		with open(filename, "rb") as f:
			with open(deltafile, "wb") as df:
				with closing(librsync.DeltaFile(signature, f)) as ldf:
					data = True
					while data:
						data = ldf.read(bufsize)
						df.write(data)
	except Exception as e:
		raise Exception(u"Failed to write delta file: %s" % forceUnicode(e))


def md5sum(filename):
	""" Returns the md5sum of the given file. """
	md5object = md5()

	with open(filename, 'rb') as fileToHash:
		while True:
			data = fileToHash.read(524288)
			if not data:
				break
			md5object.update(data)

	return md5object.hexdigest()


def randomString(length, characters=_ACCEPTED_CHARACTERS):
	"""
	Generates a random string for a given length.

	:param characters: The characters to choose from. This defaults to 0-9a-Z.
	"""
	string = [random.choice(characters) for _ in range(length)]
	return forceUnicode(u''.join(string))


def generateOpsiHostKey(forcePython=False):
	"""
	Generates an random opsi host key.

	This will try to make use of an existing random device.
	As a fallback the generation is done in plain Python.

	:param forcePython: Force the usage of Python for host key generation.
	"""
	key = u''
	if os.name == 'posix' and not forcePython:
		logger.debug(u"Opening random device '%s' to generate opsi host key" % RANDOM_DEVICE)
		with open(RANDOM_DEVICE) as r:
			key = r.read(16)
		logger.debug("Random device closed")
		key = unicode(key.encode("hex"))
	else:
		logger.debug(u"Using python random module to generate opsi host key")
		key = randomString(32, "0123456789abcdef")
	return key


def timestamp(secs=0, dateOnly=False):
	''' Returns a timestamp of the current system time format: YYYY-mm-dd[ HH:MM:SS] '''
	if not secs:
		secs = time.time()
	if dateOnly:
		return time.strftime(u"%Y-%m-%d", time.localtime(secs))
	else:
		return time.strftime(u"%Y-%m-%d %H:%M:%S", time.localtime(secs))


def objectToBeautifiedText(obj, level=0):
	if level == 0:
		obj = serialize(obj)

	indent = u' ' * (4 * level)  # indent with four spaces
	text = []
	append = text.append

	if isinstance(obj, (list, set)):
		append(indent)
		append(u'[\n')

		if obj:
			for element in obj:
				if not isinstance(element, (dict, list)):
					append(indent)
				append(objectToBeautifiedText(element, level + 1))
				append(u',')
				append(u'\n')

			del text[-2]  # Deleting the last comma

		append(indent)
		append(u']')
	elif isinstance(obj, dict):
		append(indent)
		append(u'{\n')

		if obj:
			for (key, value) in obj.iteritems():
				append(indent)
				append(key.join((u'"', u'" : ')))
				if isinstance(value, (dict, list)):
					append(u'\n')
				append(objectToBeautifiedText(value, level + 1))
				append(u',')
				append(u'\n')

			del text[-2]  # Deleting the last comma

		append(indent)
		append(u'}')
	elif isinstance(obj, str):  # TODO: watch out for Python 3
		append(toJson(forceUnicode(obj)))
	else:
		append(toJson(obj))

	return ''.join(text)


def objectToBash(obj, bashVars=None, level=0):
	"""
	:type bashVars: dict
	"""
	if bashVars is None:
		bashVars = {}

	if level == 0:
		obj = serialize(obj)

	varName = 'RESULT'
	if level > 0:
		varName = 'RESULT%d' % level

	if not bashVars.get(varName):
		bashVars[varName] = u''

	if hasattr(obj, 'serialize'):
		obj = obj.serialize()

	if isinstance(obj, (list, set)):
		bashVars[varName] += u'(\n'
		for i in range( len(obj) ):
			if isinstance(obj[i], (dict, list)):
				hashFound = True
				level += 1
				objectToBash(obj[i], bashVars, level)
				bashVars[varName] += u'RESULT%d=${RESULT%d[*]}' % (level, level)
			else:
				objectToBash(obj[i], bashVars, level)
			bashVars[varName] += u'\n'
		bashVars[varName] = bashVars[varName][:-1] + u'\n)'
	elif isinstance(obj, dict):
		bashVars[varName] += u'(\n'
		for (key, value) in obj.items():
			bashVars[varName] += '%s=' % key
			if isinstance(value, (dict, list)):
				level += 1
				v = objectToBash(value, bashVars, level)
				bashVars[varName] += u'${RESULT%d[*]}' % level
			else:
				objectToBash(value, bashVars, level)
			bashVars[varName] += u'\n'
		bashVars[varName] = bashVars[varName][:-1] + u'\n)'

	elif obj is None:
		bashVars[varName] += u'""'

	else:
		bashVars[varName] += u'"%s"' % forceUnicode(obj)

	return bashVars


def objectToHtml(obj, level=0):
	if level == 0:
		obj = serialize(obj)

	html = []
	append = html.append

	if isinstance(obj, (list, set)):
		append(u'[')
		if len(obj) > 0:
			append(u'<div style="padding-left: 3em;">')
			for i, currentElement in enumerate(obj):
				append(objectToHtml(currentElement, level + 1))
				if i < len(obj) - 1:
					append(u',<br />\n')
			append(u'</div>')
		append(u']')
	elif isinstance(obj, dict):
		append(u'{')
		if len(obj) > 0:
			append(u'<div style="padding-left: 3em;">')
			for i, (key, value) in enumerate(obj.items()):
				append(u'<font class="json_key">')
				append(objectToHtml(key))
				append(u'</font>: ')
				append(objectToHtml(value, level + 1))
				if i < len(obj) - 1:
					append(u',<br />\n')
			append(u'</div>')
		append(u'}')
	elif isinstance(obj, bool):
		append(str(obj).lower())
	elif obj is None:
		append('null')
	else:
		if isinstance(obj, (str, unicode)):  # TODO: watch out for Python 3
			append(replaceSpecialHTMLCharacters(obj).join((u'"', u'"')))
		else:
			append(replaceSpecialHTMLCharacters(obj))

	return u''.join(html)


def replaceSpecialHTMLCharacters(text):
	return forceUnicode(text)\
		.replace(u'\r', u'')\
		.replace(u'\t', u'   ')\
		.replace(u'&', u'&amp;')\
		.replace(u'"', u'&quot;')\
		.replace(u"'", u'&apos;')\
		.replace(u' ', u'&nbsp;')\
		.replace(u'<', u'&lt;')\
		.replace(u'>', u'&gt;')\
		.replace(u'\n', u'<br />\n')


def compareVersions(v1, condition, v2):
	def removePartAfterWave(versionString):
		if "~" in versionString:
			return versionString[:versionString.find("~")]
		else:
			return versionString

	def splitProductAndPackageVersion(versionString):
		productVersion = packageVersion = u'0'

		match = re.search('^\s*([\w\.]+)-*([\w\.]*)\s*$', versionString)
		if not match:
			raise Exception(u"Bad version string '%s'" % versionString)

		productVersion = match.group(1)
		if match.group(2):
			packageVersion = match.group(2)

		return (productVersion, packageVersion)

	def makeEqualLength(first, second):
		while len(first) < len(second):
			first.append(u'0')

	if not condition:
		condition = u'=='
	if condition not in (u'==', u'=', u'<', u'<=', u'>', u'>='):
		raise Exception(u"Bad condition '%s'" % condition)
	if condition == u'=':
		condition = u'=='

	v1 = removePartAfterWave(forceUnicode(v1))
	v2 = removePartAfterWave(forceUnicode(v2))

	(v1ProductVersion, v1PackageVersion) = splitProductAndPackageVersion(v1)
	(v2ProductVersion, v2PackageVersion) = splitProductAndPackageVersion(v2)

	for (v1, v2) in ( (v1ProductVersion, v2ProductVersion), (v1PackageVersion, v2PackageVersion) ):
		v1p = v1.split(u'.')
		v2p = v2.split(u'.')
		makeEqualLength(v1p, v2p)
		makeEqualLength(v2p, v1p)
		for i in range(len(v1p)):
			while (len(v1p[i]) > 0) or (len(v2p[i]) > 0):
				cv1 = u''
				cv2 = u''

				match = re.search('^(\d+)(\D*.*)$', v1p[i])
				if match:
					cv1 = int(match.group(1))
					v1p[i] = match.group(2)
				else:
					match = re.search('^(\D+)(\d*.*)$', v1p[i])
					if match:
						cv1 = match.group(1)
						v1p[i] = match.group(2)

				match = re.search('^(\d+)(\D*.*)$', v2p[i])
				if match:
					cv2 = int(match.group(1))
					v2p[i] = match.group(2)
				else:
					match = re.search('^(\D+)(\d*.*)$', v2p[i])
					if match:
						cv2 = match.group(1)
						v2p[i] = match.group(2)

				if cv1 == u'':
					cv1 = chr(1)
				if cv2 == u'':
					cv2 = chr(1)
				if cv1 == cv2:
					logger.debug2(u"%s == %s => continue" % (cv1, cv2))
					continue

				if not isinstance(cv1, int):
					cv1 = u"'%s'" % cv1
				if not isinstance(cv2, int):
					cv2 = u"'%s'" % cv2

				b = eval(u"%s %s %s" % (cv1, condition, cv2))
				logger.debug2(u"%s(%s) %s %s(%s) => %s | '%s' '%s'" % (type(cv1), cv1, condition, type(cv2), cv2, b, v1p[i], v2p[i]) )
				if not b:
					logger.debug(u"Unfulfilled condition: %s-%s %s %s-%s" \
						% (v1ProductVersion, v1PackageVersion, condition, v2ProductVersion, v2PackageVersion ))
					return False
				else:
					logger.debug(u"Fulfilled condition: %s-%s %s %s-%s" \
						% (v1ProductVersion, v1PackageVersion, condition, v2ProductVersion, v2PackageVersion ))
					return True

	if u'=' not in condition:
		logger.debug(u"Unfulfilled condition: %s-%s %s %s-%s" \
			% (v1ProductVersion, v1PackageVersion, condition, v2ProductVersion, v2PackageVersion ))
		return False

	logger.debug(u"Fulfilled condition: %s-%s %s %s-%s" \
		% (v1ProductVersion, v1PackageVersion, condition, v2ProductVersion, v2PackageVersion ))
	return True


unitRegex = re.compile('^(\d+\.*\d*)\s*([\w]{0,4})$')
def removeUnit(x):
	x = forceUnicode(x)
	match = unitRegex.search(x)
	if not match:
		return x

	if u'.' in match.group(1):
		value = float(match.group(1))
	else:
		value = int(match.group(1))

	unit = match.group(2)
	mult = 1000

	if unit.lower().endswith('hz'):
		unit = unit[:-2]
	elif unit.lower().endswith('bits'):
		mult = 1024
		unit = unit[:-4]
	elif unit.lower().endswith('b'):
		mult = 1024
		unit = unit[:-1]
	elif unit.lower().endswith('s') or unit.lower().endswith('v'):
		unit = unit[:-1]

	if unit.endswith('n'):
		return float(value) / (mult * mult)
	elif unit.endswith('m'):
		return float(value) / mult
	elif unit.lower().endswith('k'):
		return value * mult
	elif unit.endswith('M'):
		return value * mult * mult
	elif unit.endswith('G'):
		return value * mult * mult * mult

	return value


def blowfishEncrypt(key, cleartext):
	"Takes cleartext string, returns hex-encoded, blowfish-encrypted string"

	cleartext = forceUnicode(cleartext).encode('utf-8')
	key = forceUnicode(key)

	while len(cleartext) % 8 != 0:
		# Fill up with \0 until length is a mutiple of 8
		cleartext += chr(0)

	try:
		key = key.decode("hex")
	except TypeError:
		raise Exception(u"Failed to hex decode key '%s'" % key)

	blowfish = Blowfish.new(key, Blowfish.MODE_CBC, BLOWFISH_IV)
	crypt = blowfish.encrypt(cleartext)
	return unicode(crypt.encode("hex"))


def blowfishDecrypt(key, crypt):
	"Takes hex-encoded, blowfish-encrypted string, returns cleartext string"

	key = forceUnicode(key)
	crypt = forceUnicode(crypt)
	try:
		key = key.decode("hex")
	except TypeError as e:
		raise Exception(u"Failed to hex decode key '%s'" % key)
	crypt = crypt.decode("hex")
	blowfish = Blowfish.new(key, Blowfish.MODE_CBC, BLOWFISH_IV)
	cleartext = blowfish.decrypt(crypt)
	# Remove possible \0-chars
	if cleartext.find('\0') != -1:
		cleartext = cleartext[:cleartext.find('\0')]

	try:
		return unicode(cleartext, 'utf-8')
	except Exception as e:
		logger.error(e)
		raise Exception(u"Failed to decrypt")


def encryptWithPublicKeyFromX509CertificatePEMFile(data, filename):
	import M2Crypto

	with open(filename, 'r') as f:
		cert = M2Crypto.X509.load_cert_string(f.read())
		rsa = cert.get_pubkey().get_rsa()
		enc = ''
		chunks = []
		while (len(data) > 16):
			chunks.append(data[:16])
			data = data[16:]
		chunks.append(data)
		for chunk in chunks:
			enc += rsa.public_encrypt(data=chunk, padding=M2Crypto.RSA.pkcs1_oaep_padding)
		return enc


def decryptWithPrivateKeyFromPEMFile(data, filename):
	import M2Crypto
	privateKey = M2Crypto.RSA.load_key(filename)
	chunks = []
	while (len(data) > 128):
		chunks.append(data[:128])
		data = data[128:]
	chunks.append(data)
	res = ''
	for chunk in chunks:
		res += privateKey.private_decrypt(data=chunk, padding=M2Crypto.RSA.pkcs1_oaep_padding)

	if '\0' in res:
		res = res[:res.find('\0')]
	return res


def findFiles(directory, prefix=u'', excludeDir=None, excludeFile=None, includeDir=None, includeFile=None, returnDirs=True, returnLinks=True, followLinks=False, repository=None):
	directory = forceFilename(directory)
	prefix = forceUnicode(prefix)

	if excludeDir:
		if not isRegularExpressionPattern(excludeDir):
			excludeDir = re.compile(forceUnicode(excludeDir))
	else:
		excludeDir = None

	if excludeFile:
		if not isRegularExpressionPattern(excludeFile):
			excludeFile = re.compile(forceUnicode(excludeFile))
	else:
		excludeFile = None

	if includeDir:
		if not isRegularExpressionPattern(includeDir):
			includeDir = re.compile(forceUnicode(includeDir))
	else:
		includeDir = None

	if includeFile:
		if not isRegularExpressionPattern(includeFile):
			includeFile = re.compile(forceUnicode(includeFile))
	else:
		includeFile = None

	returnDirs = forceBool(returnDirs)
	returnLinks = forceBool(returnLinks)
	followLinks = forceBool(followLinks)

	islink = os.path.islink
	isdir = os.path.isdir
	listdir = os.listdir
	if repository:
		islink = repository.islink
		isdir = repository.isdir
		listdir = repository.listdir

	files = []
	for entry in listdir(directory):
		if isinstance(entry, str):  # TODO how to handle this with Python 3?
			logger.error(u"Bad filename '%s' found in directory '%s', skipping entry!" % (unicode(entry, 'ascii', 'replace'), directory))
			continue
		pp = os.path.join(prefix, entry)
		dp = os.path.join(directory, entry)
		isLink = False
		if islink(dp):
			isLink = True
			if not returnLinks and not followLinks:
				continue
		if isdir(dp) and (not isLink or followLinks):
			if excludeDir and re.search(excludeDir, entry):
				logger.debug(u"Excluding dir '%s' and containing files" % entry)
				continue
			if includeDir:
				if not re.search(includeDir, entry):
					continue
				logger.debug(u"Including dir '%s' and containing files" % entry)
			if returnDirs:
				files.append(pp)
			files.extend(
				findFiles(
					directory=dp,
					prefix=pp,
					excludeDir=excludeDir,
					excludeFile=excludeFile,
					includeDir=includeDir,
					includeFile=includeFile,
					returnDirs=returnDirs,
					returnLinks=returnLinks,
					followLinks=followLinks,
					repository=repository
				)
			)
			continue

		if excludeFile and re.search(excludeFile, entry):
			if isLink:
				logger.debug(u"Excluding link '%s'" % entry)
			else:
				logger.debug(u"Excluding file '%s'" % entry)
			continue

		if includeFile:
			if not re.search(includeFile, entry):
				continue
			if isLink:
				logger.debug(u"Including link '%s'" % entry)
			else:
				logger.debug(u"Including file '%s'" % entry)
		files.append(pp)
	return files


def isRegularExpressionPattern(object):
	return "SRE_Pattern" in str(type(object))


def ipAddressInNetwork(ipAddress, networkAddress):
	"""
	Checks if the given IP address is in the given network range.
	Returns ``True`` if the given address is part of the network.
	Returns ``False`` if the given address is not part of the network.

	:param ipAddress: The IP which we check.
	:type ipAddress: str
	:param networkAddress: The network address written with slash notation.
	:type networkAddress: str
	"""
	def createBytemaskFromAddress(address):
		"Returns an int representation of an bytemask of an ipAddress."
		num = [forceInt(part) for part in address.split('.')]
		return (num[0] << 24) + (num[1] << 16) + (num[2] << 8) + num[3]

	ipAddress = forceIPAddress(ipAddress)
	networkAddress = forceNetworkAddress(networkAddress)

	ip = createBytemaskFromAddress(ipAddress)

	network, netmask = networkAddress.split(u'/')

	if '.' not in netmask:
		netmask = forceUnicode(socket.inet_ntoa(struct.pack('>I', 0xffffffff ^ (1 << 32 - forceInt(netmask)) - 1)))

	while netmask.count('.') < 3:
		netmask = netmask + u'.0'

	logger.debug(
		u"Testing if ip {ipAddress} is part of network "
		u"{network}/{netmask}".format(
			ipAddress=ipAddress,
			network=network,
			netmask=netmask
		)
	)

	network = createBytemaskFromAddress(network)
	netmask = createBytemaskFromAddress(netmask)

	wildcard = netmask ^ 0xFFFFFFFF
	if wildcard | ip == wildcard | network:
		return True

	return False


def flattenSequence(sequence):
	"""
	Flattens nested sequences so that only a flat list will be returned.

	:returntype: list
	"""
	listToReturn = []
	for part in sequence:
		if isinstance(part, (list, tuple, set, types.GeneratorType)):
			listToReturn.extend(flattenSequence(part))
		else:
			listToReturn.append(part)
	return listToReturn


def getfqdn(name='', conf=None):
	"""
	Get the fqdn.

	If ``name`` is not given it will try various ways to get a valid
	fqdn from the current host.
	If ``conf`` but no name is given it will try to read the FQDN from
	the specified configuration file.
	"""
	if not name:
		env = os.environ.copy()
		if "OPSI_HOSTNAME" in env:
			return forceFqdn(env["OPSI_HOSTNAME"])

		if conf is not None:
			hostname = getGlobalConfig('hostname', conf)
		else:
			hostname = getGlobalConfig('hostname')

		if hostname:
			return forceFqdn(hostname)

	return forceFqdn(socket.getfqdn(name))


def getGlobalConfig(name, configFile=OPSI_GLOBAL_CONF):
	"""
	Reads the value of ``name`` from the global configuration.

	:param configFile: The path of the config file.
	:type configFile: str
	"""
	name = forceUnicode(name)
	if os.path.exists(configFile):
		with codecs.open(configFile, 'r', 'utf8') as config:
			for line in config:
				line = line.strip()
				if not line or line.startswith(('#', ';')) or '=' not in line:
					continue
				(key, value) = line.split('=', 1)
				if key.strip().lower() == name.lower():
					return value.strip()
	return None


def removeDirectory(directory):
	"""
	Removing an directory.

	If this fails with shutil it will try to use system calls.

	.. versionadded:: 4.0.5.1


	:param directory: Path to the directory
	:tye directory: str
	"""
	logger.debug('Removing directory: {0}'.format(directory))
	try:
		shutil.rmtree(directory)
	except UnicodeDecodeError:
		# See http://bugs.python.org/issue3616
		logger.info(
			u'Client data directory seems to contain filenames '
			u'with unicode characters. Trying fallback.'
		)

		import OPSI.System  # late import to avoid circular dependency
		OPSI.System.execute('rm -rf {dir}'.format(dir=directory))


def chunk(iterable, size):
	"""
	Returns chunks (parts) of a specified `size` from `iterable`.
	It will not pad (fill) the chunks.

	This works lazy and therefore can be used with any iterable without
	much overhead.

	Original recipe from http://stackoverflow.com/a/22045226
	"""
	it = iter(iterable)
	return iter(lambda: tuple(islice(it, size)), ())
