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
Tests for the dynamically loaded OPSI 3.x legacy methods.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/10_opsi.conf``.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Object import (OpsiClient, LocalbootProduct, ProductOnClient,
						 ProductDependency, OpsiDepotserver, ProductOnDepot,
						 UnicodeConfig, ConfigState)

import pytest


@pytest.yield_fixture
def prefilledBackendManager(backendManager):
	fillBackend(backendManager)
	yield backendManager


def fillBackend(backend):
	client = OpsiClient(
		id='backend-test-1.vmnat.local',
		description='Unittest Test client.'
	)

	depot = OpsiDepotserver(
		id='depotserver1.some.test',
		description='Test Depot',
	)

	backend.host_createObjects([client, depot])

	firstProduct = LocalbootProduct('to_install', '1.0', '1.0')
	secondProduct = LocalbootProduct('already_installed', '1.0', '1.0')

	prodDependency = ProductDependency(
		productId=firstProduct.id,
		productVersion=firstProduct.productVersion,
		packageVersion=firstProduct.packageVersion,
		productAction='setup',
		requiredProductId=secondProduct.id,
		# requiredProductVersion=secondProduct.productVersion,
		# requiredPackageVersion=secondProduct.packageVersion,
		requiredAction='setup',
		requiredInstallationStatus='installed',
		requirementType='after'
	)

	backend.product_createObjects([firstProduct, secondProduct])
	backend.productDependency_createObjects([prodDependency])

	poc = ProductOnClient(
		clientId=client.id,
		productId=firstProduct.id,
		productType=firstProduct.getType(),
		productVersion=firstProduct.productVersion,
		packageVersion=firstProduct.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)

	backend.productOnClient_createObjects([poc])

	firstProductOnDepot = ProductOnDepot(
		productId=firstProduct.id,
		productType=firstProduct.getType(),
		productVersion=firstProduct.productVersion,
		packageVersion=firstProduct.packageVersion,
		depotId=depot.getId(),
		locked=False
	)

	secondProductOnDepot = ProductOnDepot(
		productId=secondProduct.id,
		productType=secondProduct.getType(),
		productVersion=secondProduct.productVersion,
		packageVersion=secondProduct.packageVersion,
		depotId=depot.getId(),
		locked=False
	)

	backend.productOnDepot_createObjects([firstProductOnDepot, secondProductOnDepot])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)

	backend.config_createObjects(clientConfigDepotId)

	clientDepotMappingConfigState = ConfigState(
		configId=clientConfigDepotId.getId(),
		objectId=client.getId(),
		values=depot.getId()
	)

	backend.configState_createObjects(clientDepotMappingConfigState)


def testBackendDoesNotCreateProductsOnClientsOnItsOwn(prefilledBackendManager):
	pocs = prefilledBackendManager.productOnClient_getObjects()
	assert 1 == len(pocs), 'Expected to have only one ProductOnClient but got {n} instead: {0}'.format(pocs, n=len(pocs))


def testSetProductActionRequestWithDependenciesSetsProductsToSetup(prefilledBackendManager):
	"""
	An product action request should set product that are dependencies to \
setup even if they are already installed on a client.
	"""
	prefilledBackendManager.setProductActionRequestWithDependencies(
		'to_install',
		'backend-test-1.vmnat.local',
		'setup'
	)

	productsOnClient = prefilledBackendManager.productOnClient_getObjects()
	assert 2 == len(productsOnClient)

	productThatShouldBeReinstalled = None
	for poc in productsOnClient:
		assert 'backend-test-1.vmnat.local' == poc.clientId, 'Wrong client id. Expected it to be {0!r} but got: {1!r}'.format('backend-test-1.vmnat.local', poc.clientId)

		if poc.productId == 'already_installed':
			productThatShouldBeReinstalled = poc

	if productThatShouldBeReinstalled is None:
		raise AssertionError('Could not find a product "{0}" on the client.'.format('already_installed'))

	assert productThatShouldBeReinstalled.productId == 'already_installed'
	assert productThatShouldBeReinstalled.actionRequest == 'setup'


def testGetProductOrdering(prefilledBackendManager):
	prefilledBackendManager.getProductOrdering('depotserver1.some.test')
