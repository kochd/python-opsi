#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Testing basic backends.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os.path

from OPSI.Backend.Backend import ExtendedBackend
from OPSI.Types import BackendMissingDataError
from OPSI.Util import randomString
from .BackendTestMixins.Hosts import getConfigServer
from .helpers import workInTemporaryDirectory

import pytest


def testGettingBackendInfoWithoutBackend():
    backend = ExtendedBackend(None)
    backend.backend_info()


def testSettingAndGettingUserCredentials(fakeCredentialsBackend):
    backend = fakeCredentialsBackend

    with pytest.raises(BackendMissingDataError):
        backend.user_getCredentials('unknown')

    backend.user_setCredentials(username="hans", password='blablabla')

    credentials = backend.user_getCredentials(username="hans")
    assert 'blablabla' == credentials['password']


def testOverWritingOldCredentials(fakeCredentialsBackend):
    backend = fakeCredentialsBackend

    backend.user_setCredentials(username="hans", password='bla')
    backend.user_setCredentials(username="hans", password='itworks')

    credentials = backend.user_getCredentials(username="hans")
    assert 'itworks' == credentials['password']


def testWorkingWithManyCredentials(fakeCredentialsBackend):
    backend = fakeCredentialsBackend

    for _ in range(100):
        backend.user_setCredentials(username=randomString(12),
                                    password=randomString(12))
    backend.user_setCredentials(username="hans", password='bla')

    credentials = backend.user_getCredentials(username="hans")
    assert 'bla' == credentials['password']


def testSettingUserCredentialsWithoutDepot(fakeCredentialsBackend):
    backend = fakeCredentialsBackend
    backend.host_deleteObjects(backend.host_getObjects())

    with pytest.raises(Exception):
        backend.user_setCredentials("hans", '')


@pytest.yield_fixture
def fakeCredentialsBackend(configDataBackend):
    backend = configDataBackend
    backend.host_insertObject(getConfigServer())  # Required for file backend.

    with workInTemporaryDirectory() as tempDir:
        credFile = os.path.join(tempDir, 'credentials')
        with open(credFile, 'w'):
            pass

        originalFile = backend._opsiPasswdFile
        backend._opsiPasswdFile = credFile
        try:
            yield backend
        finally:
            backend._opsiPasswdFile = originalFile
