#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013 uib GmbH <info@uib.de>

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
opsi python library - Util - Task - Certificate

Functionality to work with certificates.
Certificates play an important role in the encrypted communication
between servers and clients.

.. versionadded:: 4.0.4

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import unicode_literals

import os
import shutil
from OpenSSL import crypto, rand
from tempfile import NamedTemporaryFile

from OPSI.Logger import Logger
from OPSI.System import which, execute
from OPSI.Types import forceHostId, forceInt
from OPSI.Util import getfqdn

OPSI_GLOBAL_CONF = u'/etc/opsi/global.conf'
OPSICONFD_CERTFILE = u"/etc/opsi/opsiconfd.pem"
DEFAULT_CERTIFICATE_PARAMETERS = {
	"country": "DE",
	"state": "RP",
	"locality": "Mainz",
	"organization": "uib gmbh",
	"organizationalUnit": "",
	"commonName": forceHostId(getfqdn(conf=OPSI_GLOBAL_CONF)),
	"emailAddress": "",
	"expires": 2,
}
LOGGER = Logger()


class NoCertificateError(Exception):
	pass


class CertificateCreationError(Exception):
	pass


def renewCertificate(path=None):
	"""
	Renews an existing certificate.

	:param path: The path of the certificate.
	:type path: str
	"""
	if path is None:
		path = OPSICONFD_CERTFILE

	if not os.path.exists(path):
		raise NoCertificateError('No certificate found at {0}'.format(path))

	currentConfig = loadConfigurationFromCertificate(path)

	backupfile = ''.join((path, ".bak"))
	LOGGER.notice("Backup existing certifcate to {0}".format(backupfile))
	shutil.copy(path, backupfile)

	createCertificate(path, currentConfig)


def createCertificate(path=None, config=None):
	"""
	Creates a certificate.

	:param path: The path of the certificate. \
If this is `None` the default will be used.
	:type path: str
	:param config: The configuration of the certificate. If not given will use a default.
	:type config: dict
	"""
	# TODO: check if path exists and give user info about it

	try:
		which("ucr")
		LOGGER.notice(u"Don't use recreate method on UCS-Systems")
		return
	except Exception:
		pass

	if path is None:
		path = OPSICONFD_CERTFILE

	if config is None:
		certparams = DEFAULT_CERTIFICATE_PARAMETERS
		certparams['emailAddress'] = 'root@localhost'
		certparams['organizationalUnit'] = 'OPSI'
	else:
		certparams = config

	try:
		certparams["expires"] = forceInt(certparams["expires"])
	except Exception:
		raise CertificateCreationError("No valid expiration date given. "
									   "Must be an integer.")

	if certparams["commonName"] != forceHostId(getfqdn(conf=OPSI_GLOBAL_CONF)):
		raise CertificateCreationError("commonName must be the FQDN of the "
									   "local server")

	LOGGER.notice(u"Creating new opsiconfd cert")
	LOGGER.notice(u"Generating new key pair")
	k = crypto.PKey()
	k.generate_key(crypto.TYPE_RSA, 1024)

	LOGGER.notice(u"Generating new self-signed cert")
	cert = crypto.X509()
	cert.get_subject().C = certparams['country']
	cert.get_subject().ST = certparams['state']
	cert.get_subject().L = certparams['locality']
	cert.get_subject().O = certparams['organization']
	cert.get_subject().OU = certparams['organizationalUnit']
	cert.get_subject().CN = certparams['commonName']
	cert.get_subject().emailAddress = certparams['emailAddress']

	LOGGER.notice(u"Generating new Serialnumber")
	#TODO: generating serial number
	#TODO: some info on the serial number: https://tools.ietf.org/html/rfc2459#page-18
	cert.set_serial_number(1000)
	LOGGER.notice(u"Setting new expiration date (%d years)" % certparams["expires"])
	cert.gmtime_adj_notBefore(0)
	cert.gmtime_adj_notAfter(certparams["expires"] * 365 * 24 * 60 * 60)

	LOGGER.notice(u"Filling certificate with new data")
	cert.set_issuer(cert.get_subject())
	cert.set_pubkey(k)
	cert.set_version(2)

	LOGGER.notice(u"Signing Certificate")
	cert.sign(k, 'sha1')

	certcontext = "".join((
		crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
		crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
	)

	LOGGER.notice(u"Beginning to write certificate.")
	with open(path, "wt") as certfile:
		certfile.write(certcontext)

	with NamedTemporaryFile(mode="wt") as randfile:
		LOGGER.notice(u"Generating and filling new randomize string")
		randfile.write(rand.bytes(512))

		execute(
			"{command} gendh -rand {tempfile} 512 >> {target}".format(
				command=which("openssl"), tempfile=randfile.name, target=path
			)
		)

	LOGGER.notice('Certificate creation done.')


def loadConfigurationFromCertificate(path=None):
	"""
	Loads certificate configuration from a file.

	:param path: The path to the certificate. \
Uses `OPSICONFD_CERTFILE` if no path is given.
	:type path: str
	:return: The configuration as read from the certificate.
	:rtype: dict
	"""
	if path is None:
		path = OPSICONFD_CERTFILE

	if not os.path.exists(path):
		raise NoCertificateError('No certificate found at "{path}".'.format(path=path))

	certparams = {}
	with open(path) as data:
		cert = crypto.load_certificate(crypto.FILETYPE_PEM, data.read())

		certparams["country"] = cert.get_subject().C
		certparams["state"] = cert.get_subject().ST
		certparams["locality"] = cert.get_subject().L
		certparams["organization"] = cert.get_subject().O
		certparams["organizationalUnit"] = cert.get_subject().OU
		certparams["commonName"] = cert.get_subject().CN
		certparams["emailAddress"] = cert.get_subject().emailAddress

	return certparams
