#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Object    =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.5'

# imports
import json, re, copy, time, inspect

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Tools import generateOpsiHostKey, timestamp


# Get logger instance
logger = Logger()

def deserialize(obj):
	newObj = None
	if type(obj) is dict and obj.has_key('type'):
		try:
			c = eval('%s' % obj['type'])
			newObj = c.fromHash(obj)
		except Exception, e:
			logger.debug(e)
			return obj
	elif type(obj) is list:
		newObj = []
		for o in obj:
			newObj.append(deserialize(o))
	elif type(obj) is dict:
		newObj = {}
		for (k, v) in obj.items():
			newObj[k] = deserialize(v)
	else:
		return obj
	return newObj

def serialize(obj):
	newObj = None
	if hasattr(obj, 'serialize'):
		newObj = obj.serialize()
	elif type(obj) is list:
		newObj = []
		for o in obj:
			newObj.append(serialize(o))
	elif type(obj) is dict:
		newObj = {}
		for (k, v) in obj.items():
			newObj[k] = serialize(v)
	else:
		return obj
	return newObj

def mandatoryConstructorArgs(Class):
	(args, varargs, varkwargs, defaults) = inspect.getargspec(Class.__init__)
	if not defaults:
		defaults = []
	last = -1*len(defaults)
	if (last == 0):
		last = len(args)
	mandatory = args[1:][:last]
	logger.debug2(u"mandatoryConstructorArgs for %s: %s" % (Class, mandatory))
	return mandatory

def getIdentAttributes(Class):
	return tuple(mandatoryConstructorArgs(Class))

def getForeignIdAttributes(Class):
	return Class.foreignIdAttributes
	
def getPossibleClassAttributes(Class):
	attributes = inspect.getargspec(Class.__init__)[0]
	for subClass in Class.subClasses.values():
		attributes.extend(inspect.getargspec(subClass.__init__)[0])
	attributes = list(set(attributes))
	attributes.remove('self')
	attributes.append('type')
	return attributes

def getBackendMethodPrefix(Class):
	return Class.backendMethodPrefix
	
class BaseObject(object):
	subClasses = {}
	identSeparator = u';'
	foreignIdAttributes = []
	backendMethodPrefix = ''
	
	def getBackendMethodPrefix(self):
		return self.backendMethodPrefix
	
	def getForeignIdAttributes(self):
		return self.foreignIdAttributes
	
	def getIdentAttributes(self):
		return getIdentAttributes(self.__class__)
	
	def getIdent(self, returnType='unicode'):
		returnType = forceUnicodeLower(returnType)
		identAttributes = self.getIdentAttributes()
		identValues = []
		for attr in identAttributes:
			identValues.append(getattr(self, attr))
		if returnType in ('list'):
			return identValues
		elif returnType in ('tuple'):
			return tuple(identValues)
		elif returnType in ('dict', 'hash'):
			ret = {}
			for i in range(len(identAttributes)):
				ret[identAttributes[i]] = identValues[i]
			return ret
		else:
			return self.identSeparator.join(identValues)
	
	def setDefaults(self):
		pass
	
	def getType(self):
		return unicode(self.__class__.__name__)
	
	def __unicode__(self):
		return u"<%s'>" % self.getType()
	
	def __str__(self):
		return unicode(self).encode("utf-8")
	
	__repr__ = __unicode__
	 
	
class Entity(BaseObject):
	subClasses = {}
	
	def setDefaults(self):
		BaseObject.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Entity'
		Class = eval(hash['type'])
		kwargs = {}
		for varname in Class.__init__.func_code.co_varnames[1:]:
			if hash.has_key(varname):
				kwargs[varname] = hash[varname]
		return Class(**kwargs)
	
	def toHash(self):
		hash = copy.deepcopy(self.__dict__)
		hash['type'] = self.getType()
		return hash
	
	def serialize(self):
		hash = self.toHash()
		hash['ident'] = self.getIdent()
		return hash
	
	@staticmethod
	def fromJson(jsonString):
		return Entity.fromHash(json.loads(jsonString))

BaseObject.subClasses['Entity'] = Entity

class Relationship(BaseObject):
	subClasses = {}
	
	def setDefaults(self):
		BaseObject.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Relationship'
		Class = eval(hash['type'])
		kwargs = {}
		for varname in Class.__init__.func_code.co_varnames[1:]:
			if hash.has_key(varname):
				kwargs[varname] = hash[varname]
		return Class(**kwargs)
	
	def toHash(self):
		return copy.deepcopy(self.__dict__)
	
	def serialize(self):
		hash = self.toHash()
		hash['type'] = self.getType()
		hash['ident'] = self.getIdent()
		return hash
		
	@staticmethod
	def fromJson(jsonString):
		return Relationship.fromHash(json.loads(jsonString))
	
	def toJson(self):
		return json.dumps(self.toHash())
	
BaseObject.subClasses['Relationship'] = Relationship

class Object(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['objectId']
	
	def __init__(self, id, description=None, notes=None):
		self.description = None
		self.notes = None
		self.setId(id)
		if not description is None:
			self.setDescription(description)
		if not notes is None:
			self.setNotes(notes)
	
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.notes is None:
			self.setNotes(u"")
	
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceObjectId(id)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getNotes(self):
		return self.notes
	
	def setNotes(self, notes):
		self.notes = forceUnicode(notes)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Object'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Object.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s'>" \
			% (self.getType(), self.id, self.description, self.notes)

Entity.subClasses['Object'] = Object

class Host(Object):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['hostId']
	backendMethodPrefix = 'host'
	
	def __init__(self, id, description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None):
		Object.__init__(self, id, description, notes)
		self.hardwareAddress = None
		self.ipAddress = None
		self.inventoryNumber = None
		self.setId(id)
		if not hardwareAddress is None:
			self.setHardwareAddress(hardwareAddress)
		if not ipAddress is None:
			self.setIpAddress(ipAddress)
		if not inventoryNumber is None:
			self.setInventoryNumber(inventoryNumber)
	
	def setDefaults(self):
		Object.setDefaults(self)
		if self.inventoryNumber is None:
			self.setInventoryNumber(u"")
		
	def setId(self, id):
		self.id = forceHostId(id)
	
	def getHardwareAddress(self):
		return self.hardwareAddress
	
	def setHardwareAddress(self, hardwareAddress):
		self.hardwareAddress = forceHardwareAddress(hardwareAddress)
	
	def getIpAddress(self):
		return self.ipAddress
	
	def setIpAddress(self, ipAddress):
		self.ipAddress = forceIPAddress(ipAddress)
	
	def getInventoryNumber(self):
		return self.inventoryNumber
	
	def setInventoryNumber(self, inventoryNumber):
		self.inventoryNumber = forceUnicode(inventoryNumber)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Host'
		return Object.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Host.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.hardwareAddress, self.ipAddress)
	
Object.subClasses['Host'] = Host

class OpsiClient(Host):
	subClasses = {}
	foreignIdAttributes = Host.foreignIdAttributes + ['clientId']
	
	def __init__(self, id, opsiHostKey=None, description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, created=None, lastSeen=None):
		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress, inventoryNumber)
		self.opsiHostKey = None
		self.created = None
		self.lastSeen = None
		if not opsiHostKey is None:
			self.setOpsiHostKey(opsiHostKey)
		if not created is None:
			self.setCreated(created)
		if not lastSeen is None:
			self.setLastSeen(lastSeen)
	
	def setDefaults(self):
		Host.setDefaults(self)
		if self.opsiHostKey is None:
			self.setOpsiHostKey(generateOpsiHostKey())
		if self.created is None:
			self.setCreated(timestamp())
	
	def getLastSeen(self):
		return self.lastSeen
	
	def setLastSeen(self, lastSeen):
		self.lastSeen = forceOpsiTimestamp(lastSeen)
	
	def getCreated(self):
		return self.created
	
	def setCreated(self, created):
		self.created = forceOpsiTimestamp(created)
	
	def getOpsiHostKey(self):
		return self.opsiHostKey
	
	def setOpsiHostKey(self, opsiHostKey):
		self.opsiHostKey = forceOpsiHostKey(opsiHostKey)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OpsiClient'
		return Host.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OpsiClient.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.hardwareAddress, self.ipAddress)
	
Host.subClasses['OpsiClient'] = OpsiClient

class OpsiDepotserver(Host):
	subClasses = {}
	foreignIdAttributes = Host.foreignIdAttributes + ['depotId']
	
	def __init__(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
		     description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, networkAddress=None, maxBandwidth=None):
		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress, inventoryNumber)
		self.opsiHostKey = None
		self.depotLocalUrl = None
		self.depotRemoteUrl = None
		self.repositoryLocalUrl = None
		self.repositoryRemoteUrl = None
		self.networkAddress = None
		self.maxBandwidth = None
		if not opsiHostKey is None:
			self.setOpsiHostKey(opsiHostKey)
		if not depotLocalUrl is None:
			self.setDepotLocalUrl(depotLocalUrl)
		if not depotRemoteUrl is None:
			self.setDepotRemoteUrl(depotRemoteUrl)
		if not repositoryLocalUrl is None:
			self.setRepositoryLocalUrl(repositoryLocalUrl)
		if not repositoryRemoteUrl is None:
			self.setRepositoryRemoteUrl(repositoryRemoteUrl)
		if not networkAddress is None:
			self.setNetworkAddress(networkAddress)
		if not maxBandwidth is None:
			self.setMaxBandwidth(maxBandwidth)
		
	def setDefaults(self):
		Host.setDefaults(self)
		if self.opsiHostKey is None:
			self.setOpsiHostKey(Tools.generateOpsiHostKey())
	
	def getOpsiHostKey(self):
		return self.opsiHostKey
	
	def setOpsiHostKey(self, opsiHostKey):
		self.opsiHostKey = forceOpsiHostKey(opsiHostKey)
	
	def getDepotLocalUrl(self):
		return self.depotLocalUrl
	
	def setDepotLocalUrl(self, depotLocalUrl):
		self.depotLocalUrl = forceUrl(depotLocalUrl)
	
	def getDepotRemoteUrl(self):
		return self.depotRemoteUrl
	
	def setDepotRemoteUrl(self, depotRemoteUrl):
		self.depotRemoteUrl = forceUrl(depotRemoteUrl)
	
	def getRepositoryLocalUrl(self):
		return self.repositoryLocalUrl
	
	def setRepositoryLocalUrl(self, repositoryLocalUrl):
		self.repositoryLocalUrl = forceUrl(repositoryLocalUrl)
	
	def getRepositoryRemoteUrl(self):
		return self.repositoryRemoteUrl
	
	def setRepositoryRemoteUrl(self, repositoryRemoteUrl):
		self.repositoryRemoteUrl = forceUrl(repositoryRemoteUrl)
	
	def getNetworkAddress(self):
		return self.networkAddress
	
	def setNetworkAddress(self, networkAddress):
		self.networkAddress = forceNetworkAddress(networkAddress)
	
	def getMaxBandwidth(self):
		return self.maxBandwidth
	
	def setMaxBandwidth(self, maxBandwidth):
		self.maxBandwidth = forceInt(maxBandwidth)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OpsiDepotserver'
		return Host.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OpsiDepotserver.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.hardwareAddress, self.ipAddress)
	
Host.subClasses['OpsiDepotserver'] = OpsiDepotserver

class OpsiConfigserver(OpsiDepotserver):
	subClasses = {}
	foreignIdAttributes = OpsiDepotserver.foreignIdAttributes + ['serverId']
	
	def __init__(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
		     description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, networkAddress=None, maxBandwidth=None):
		OpsiDepotserver.__init__(self, id, opsiHostKey, depotLocalUrl, depotRemoteUrl, repositoryLocalUrl, repositoryRemoteUrl,
		     description, notes, hardwareAddress, ipAddress, inventoryNumber, networkAddress, maxBandwidth)
	
	def setDefaults(self):
		OpsiDepotserver.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OpsiConfigserver'
		return OpsiDepotserver.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OpsiConfigserver.fromHash(json.loads(jsonString))
	
OpsiDepotserver.subClasses['OpsiConfigserver'] = OpsiConfigserver
Host.subClasses['OpsiConfigserver'] = OpsiConfigserver

class Config(Entity):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['configId']
	backendMethodPrefix = 'config'
	
	def __init__(self, id, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		self.description = None
		self.possibleValues = None
		self.defaultValues = None
		self.editable = None
		self.multiValue = None
		
		self.setId(id)
		if not description is None:
			self.setDescription(description)
		if not possibleValues is None:
			self.setPossibleValues(possibleValues)
		if not defaultValues is None:
			self.setDefaultValues(defaultValues)
		if not editable is None:
			self.setEditable(editable)
		if not multiValue is None:
			self.setMultiValue(multiValue)
	
	def setDefaults(self):
		Entity.setDefaults(self)
		self.setDefaultValues(self.defaultValues)
	
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceUnicodeLower(id)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getPossibleValues(self):
		return self.possibleValues
	
	def setPossibleValues(self, possibleValues):
		self.possibleValues = forceList(possibleValues)
	
	def getDefaultValues(self):
		return self.defaultValues
	
	def setDefaultValues(self, defaultValues):
		self.defaultValues = forceList(defaultValues)
		if self.possibleValues is None:
			self.possibleValues = []
		for defaultValue in self.defaultValues:
			if not defaultValue in self.possibleValues:
				self.possibleValues.append(defaultValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
	
	def getEditable(self):
		return self.editable
	
	def setEditable(self, editable):
		self.editable = forceBool(editable)
	
	def getMultiValue(self):
		return self.multiValue
	
	def setMultiValue(self, multiValue):
		self.multiValue = forceBool(multiValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Config'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Config.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', possibleValues %s, defaultValues %s, multiValue: %s>" \
			% (self.getType(), self.id, self.description, self.possibleValues, self.defaultValues, self.multiValue)
	
Entity.subClasses['Config'] = Config

class UnicodeConfig(Config):
	subClasses = {}
	
	def __init__(self, id, description='', possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		Config.__init__(self, id, description, possibleValues, defaultValues, editable, multiValue)
		if not possibleValues is None:
			self.setPossibleValues(possibleValues)
		if not defaultValues is None:
			self.setDefaultValues(defaultValues)
		
	def setDefaults(self):
		Config.setDefaults(self)
		if self.editable is None:
			self.editable = True
		if self.multiValue is None:
			self.multiValue = False
		if self.possibleValues is None:
			self.possibleValues = [u'']
		if self.defaultValues is None:
			self.defaultValues = [u'']
	
	def setPossibleValues(self, possibleValues):
		possibleValues = forceUnicodeList(possibleValues)
		Config.setPossibleValues(self, possibleValues)
	
	def setDefaultValues(self, defaultValues):
		defaultValues = forceUnicodeList(defaultValues)
		Config.setDefaultValues(self, defaultValues)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'UnicodeConfig'
		return Config.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return UnicodeConfig.fromHash(json.loads(jsonString))
	
Config.subClasses['UnicodeConfig'] = UnicodeConfig

class BoolConfig(Config):
	subClasses = {}
	
	def __init__(self, id, description = None, defaultValues = None):
		Config.__init__(self, id, description, [ True, False ], defaultValues, False, False)
	
	def setDefaults(self):
		Config.setDefaults(self)
	
	def setPossibleValues(self, possibleValues):
		possibleValues = [ True, False ]
		Config.setPossibleValues(self, possibleValues)
	
	def setDefaultValues(self, defaultValues):
		defaultValues = forceBoolList(defaultValues)
		if (len(defaultValues) > 1):
			raise BackendBadValueError(u"Bool config cannot have multiple default values: %s" % defaultValues)
		Config.setDefaultValues(self, defaultValues)
		
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'BoolConfig'
		return Config.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return BoolConfig.fromHash(json.loads(jsonString))
	
Config.subClasses['BoolConfig'] = BoolConfig

class ConfigState(Relationship):
	subClasses = {}
	backendMethodPrefix = 'configState'
	
	def __init__(self, configId, objectId, values=None):
		self.values = None
		self.setConfigId(configId)
		self.setObjectId(objectId)
		if not values is None:
			self.setValues(values)
	
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.values is None:
			self.setValues([])
	
	def getObjectId(self):
		return self.objectId
	
	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)
	
	def getConfigId(self):
		return self.configId
	
	def setConfigId(self, configId):
		self.configId = forceUnicodeLower(configId)
	
	def getValues(self):
		return self.values
	
	def setValues(self, values):
		self.values = forceList(values)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ConfigState'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ConfigState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s configId '%s', objectId '%s'>" \
			% (self.getType(), self.configId, self.objectId)
	
Relationship.subClasses['ConfigState'] = ConfigState

class Product(Entity):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['productId']
	backendMethodPrefix = 'product'
	
	def __init__(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
		     setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None, customScript=None, userLoginScript=None,
		     priority=None, description=None, advice=None, changelog=None, productClassIds=None, windowsSoftwareIds=None):
		self.name = None
		self.licenseRequired = None
		self.setupScript = None
		self.uninstallScript = None
		self.updateScript = None
		self.alwaysScript = None
		self.onceScript = None
		self.customScript = None
		self.userLoginScript = None
		self.priority = None
		self.description = None
		self.advice = None
		self.changelog = None
		self.productClassIds = None
		self.windowsSoftwareIds = None
		self.setId(id)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		if not name is None:
			self.setName(name)
		if not licenseRequired is None:
			self.setLicenseRequired(licenseRequired)
		if not setupScript is None:
			self.setSetupScript(setupScript)
		if not uninstallScript is None:
			self.setUninstallScript(uninstallScript)
		if not updateScript is None:
			self.setUpdateScript(updateScript)
		if not alwaysScript is None:
			self.setAlwaysScript(alwaysScript)
		if not onceScript is None:
			self.setOnceScript(onceScript)
		if not customScript is None:
			self.setCustomScript(customScript)
		if not userLoginScript is None:
			self.setUserLoginScript(userLoginScript)
		if not priority is None:
			self.setPriority(priority)
		if not description is None:
			self.setDescription(description)
		if not advice is None:
			self.setAdvice(advice)
		if not changelog is None:
			self.setChangelog(changelog)
		if not productClassIds is None:
			self.setProductClassIds(productClassIds)
		if not windowsSoftwareIds is None:
			self.setWindowsSoftwareIds(windowsSoftwareIds)
	
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.name is None:
			self.setName(u"")
		if self.licenseRequired is None:
			self.setLicenseRequired(False)
		if self.setupScript is None:
			self.setSetupScript(u"")
		if self.uninstallScript is None:
			self.setUninstallScript(u"")
		if self.updateScript is None:
			self.setUpdateScript(u"")
		if self.alwaysScript is None:
			self.setAlwaysScript(u"")
		if self.onceScript is None:
			self.setOnceScript(u"")
		if self.customScript is None:
			self.setCustomScript(u"")
		if self.userLoginScript is None:
			self.setUserLoginScript(u"")
		if self.priority is None:
			self.setPriority(0)
		if self.description is None:
			self.setDescription(u"")
		if self.advice is None:
			self.setAdvice(u"")
		if self.changelog is None:
			self.setChangelog(u"")
		if self.productClassIds is None:
			self.setProductClassIds([])
		if self.windowsSoftwareIds is None:
			self.setWindowsSoftwareIds([])
		
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceProductId(id)
	
	def getProductVersion(self):
		return self.productVersion
	
	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)
	
	def getPackageVersion(self):
		return self.packageVersion
	
	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)
	
	def getName(self):
		return self.name
	
	def setName(self, name):
		self.name = forceUnicode(name)
	
	def getLicenseRequired(self):
		return self.licenseRequired
	
	def setLicenseRequired(self, licenseRequired):
		self.licenseRequired = forceBool(licenseRequired)
	
	def getSetupScript(self):
		return self.setupScript
	
	def setSetupScript(self, setupScript):
		self.setupScript = forceFilename(setupScript)
	
	def getUninstallScript(self):
		return self.uninstallScript
	
	def setUninstallScript(self, uninstallScript):
		self.uninstallScript = forceFilename(uninstallScript)
	
	def getUpdateScript(self):
		return self.updateScript
	
	def setUpdateScript(self, updateScript):
		self.updateScript = forceFilename(updateScript)
	
	def getAlwaysScript(self):
		return self.alwaysScript
	
	def setAlwaysScript(self, alwaysScript):
		self.alwaysScript = forceFilename(alwaysScript)
	
	def getOnceScript(self):
		return self.onceScript
	
	def setOnceScript(self, onceScript):
		self.onceScript = forceFilename(onceScript)
	
	def getCustomScript(self):
		return self.customScript
	
	def setCustomScript(self, customScript):
		self.customScript = forceFilename(customScript)
	
	def getUserLoginScript(self):
		return self.userLoginScript
	
	def setUserLoginScript(self, userLoginScript):
		self.userLoginScript = forceFilename(userLoginScript)
	
	def getPriority(self):
		return self.priority
	
	def setPriority(self, priority):
		self.priority = forceProductPriority(priority)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getAdvice(self):
		return self.advice
	
	def setAdvice(self, advice):
		self.advice = forceUnicode(advice)
	
	def getChangelog(self):
		return self.changelog
	
	def setChangelog(self, changelog):
		self.changelog = forceUnicode(changelog)
	
	def getProductClassIds(self):
		return self.productClassIds
	
	def setProductClassIds(self, productClassIds):
		self.productClassIds = forceUnicodeList(productClassIds)
	
	def getWindowsSoftwareIds(self):
		return self.windowsSoftwareIds
	
	def setWindowsSoftwareIds(self, windowsSoftwareIds):
		self.windowsSoftwareIds = forceUnicodeList(windowsSoftwareIds)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Product'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Product.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', name '%s'>" \
			% (self.getType(), self.id, self.name)
	
Entity.subClasses['Product'] = Product

class LocalbootProduct(Product):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
		     setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None, customScript=None, userLoginScript=None,
		     priority=None, description=None, advice=None, changelog=None, productClassNames=None, windowsSoftwareIds=None):
		Product.__init__(self, id, productVersion, packageVersion, name, licenseRequired,
		     setupScript, uninstallScript, updateScript, alwaysScript, onceScript, customScript, userLoginScript,
		     priority, description, advice, changelog, productClassNames, windowsSoftwareIds)
	
	def setDefaults(self):
		Product.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'LocalbootProduct'
		return Product.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return LocalbootProduct.fromHash(json.loads(jsonString))
	
Product.subClasses['LocalbootProduct'] = LocalbootProduct

class NetbootProduct(Product):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
		     setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None, customScript=None,
		     priority=None, description=None, advice=None, changelog=None, productClassNames=None, windowsSoftwareIds=None,
		     pxeConfigTemplate=''):
		Product.__init__(self, id, productVersion, packageVersion, name, licenseRequired,
		     setupScript, uninstallScript, updateScript, alwaysScript, onceScript, customScript, None,
		     priority, description, advice, changelog, productClassNames, windowsSoftwareIds)
		self.pxeConfigTemplate = forceFilename(pxeConfigTemplate)
	
	def setDefaults(self):
		Product.setDefaults(self)
	
	def getPxeConfigTemplate(self):
		return self.pxeConfigTemplate
	
	def setPxeConfigTemplate(self, pxeConfigTemplate):
		self.pxeConfigTemplate = forceFilename(pxeConfigTemplate)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'NetbootProduct'
		return Product.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return NetbootProduct.fromHash(json.loads(jsonString))
	
Product.subClasses['NetbootProduct'] = NetbootProduct

class ProductProperty(Entity):
	subClasses = {}
	backendMethodPrefix = 'productProperty'
	
	def __init__(self, productId, productVersion, packageVersion, propertyId, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		self.description = None
		self.possibleValues = None
		self.defaultValues = None
		self.editable = None
		self.multiValue = None
		self.setProductId(productId)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setPropertyId(propertyId)
		if not description is None:
			self.setDescription(description)
		if not possibleValues is None:
			self.setPossibleValues(possibleValues)
		if not defaultValues is None:
			self.setDefaultValues(defaultValues)
		if not editable is None:
			self.setEditable(editable)
		if not multiValue is None:
			self.setMultiValue(multiValue)
	
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.possibleValues is None:
			self.setPossibleValues([])
		if self.defaultValues is None:
			self.setDefaultValues([])
		if self.editable is None:
			self.setEditable(True)
		if self.multiValue is None:
			self.setMultiValue(False)
		
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getProductVersion(self):
		return self.productVersion
	
	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)
	
	def getPackageVersion(self):
		return self.packageVersion
	
	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)
	
	def getPropertyId(self):
		return self.propertyId
	
	def setPropertyId(self, propertyId):
		self.propertyId = forceUnicodeLower(propertyId)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getPossibleValues(self):
		return self.possibleValues
	
	def setPossibleValues(self, possibleValues):
		self.possibleValues = forceList(possibleValues)
	
	def getDefaultValues(self):
		return self.defaultValues
	
	def setDefaultValues(self, defaultValues):
		self.defaultValues = forceList(defaultValues)
	
	def getEditable(self):
		return self.editable
	
	def setEditable(self, editable):
		self.editable = forceBool(editable)
	
	def getMultiValue(self):
		return self.multiValue
	
	def setMultiValue(self, multiValue):
		self.multiValue = forceBool(multiValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductProperty'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductProperty.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s propertyId '%s', description '%s', possibleValues %s, defaultValues %s, multiValue: %s>" \
			% (self.getType(), self.propertyId, self.description, self.possibleValues, self.defaultValues, self.multiValue)
	
Entity.subClasses['ProductProperty'] = ProductProperty

class UnicodeProductProperty(ProductProperty):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, propertyId, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		ProductProperty.__init__(self, productId, productVersion, packageVersion, propertyId, description, possibleValues, defaultValues, editable, multiValue)
		self.possibleValues = None
		self.defaultValues = None
		if not possibleValues is None:
			self.setPossibleValues(possibleValues)
		if not defaultValues is None:
			self.setDefaultValues(defaultValues)
	
	def setDefaults(self):
		ProductProperty.setDefaults(self)
	
	def setPossibleValues(self, possibleValues):
		self.possibleValues = forceUnicodeList(possibleValues)
		if self.possibleValues and self.defaultValues:
			for defaultValue in self.defaultValues:
				if not defaultValue in self.possibleValues:
					raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
						% (defaultValue, possibleValues))
		elif not self.possibleValues and self.defaultValues:
			self.possibleValues = self.defaultValues
	
	def setDefaultValues(self, defaultValues):
		self.defaultValues = forceUnicodeList(defaultValues)
		if self.possibleValues and self.defaultValues:
			for defaultValue in self.defaultValues:
				if not defaultValue in self.possibleValues:
					raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
						% (defaultValue, possibleValues))
		elif not self.possibleValues and self.defaultValues:
			self.possibleValues = self.defaultValues
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'UnicodeProductProperty'
		return ProductProperty.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return UnicodeProductProperty.fromHash(json.loads(jsonString))
	
ProductProperty.subClasses['UnicodeProductProperty'] = UnicodeProductProperty

class BoolProductProperty(ProductProperty):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, propertyId, description=None, defaultValues=None):
		ProductProperty.__init__(self, productId, productVersion, packageVersion, propertyId, description, [ True, False ], defaultValues, False, False)
		if (len(self.defaultValues) > 1):
			raise BackendBadValueError(u"Bool product property cannot have multiple default values: %s" % self.defaultValues)
	
	def setDefaults(self):
		ProductProperty.setDefaults(self)
	
	def setPossibleValues(self, possibleValues):
		self.possibleValues = [ True, False ]
	
	def setDefaultValues(self, defaultValues):
		self.defaultValues = forceBoolList(defaultValues)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'BoolProductProperty'
		return ProductProperty.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return BoolProductProperty.fromHash(json.loads(jsonString))
	
ProductProperty.subClasses['BoolProductProperty'] = BoolProductProperty

class ProductDependency(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productDependency'
	
	def __init__(self, productId, productVersion, packageVersion, productAction, requiredProductId, requiredProductVersion=None, requiredPackageVersion=None, requiredAction=None, requiredInstallationStatus=None, requirementType=None):
		self.requiredProductVersion = None
		self.requiredPackageVersion = None
		self.requiredAction = None
		self.requiredInstallationStatus = None
		self.requirementType = None
		self.setProductId(productId)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setProductAction(productAction)
		self.setRequiredProductId(requiredProductId)
		if not requiredProductVersion is None:
			self.setRequiredProductVersion(requiredProductVersion)
		if not requiredPackageVersion is None:
			self.setRequiredPackageVersion(requiredPackageVersion)
		if not requiredAction is None:
			self.setRequiredAction(requiredAction)
		if not requiredInstallationStatus is None:
			self.setRequiredInstallationStatus(requiredInstallationStatus)
		if not requirementType is None:
			self.setRequirementType(requirementType)
	
	def setDefaults(self):
		Relationship.setDefaults(self)
	
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getProductVersion(self):
		return self.productVersion
	
	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)
	
	def getPackageVersion(self):
		return self.packageVersion
	
	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)
	
	def getProductAction(self):
		return self.productAction
	
	def setProductAction(self, productAction):
		self.productAction = forceActionRequest(productAction)
	
	def getRequiredProductId(self):
		return self.requiredProductId
	
	def setRequiredProductId(self, requiredProductId):
		self.requiredProductId = forceProductId(requiredProductId)
	
	def getRequiredProductVersion(self):
		return self.requiredProductVersion
	
	def setRequiredProductVersion(self, requiredProductVersion):
		self.requiredProductVersion = forceProductVersion(requiredProductVersion)
	
	def getRequiredPackageVersion(self):
		return self.requiredPackageVersion
	
	def setRequiredPackageVersion(self, requiredPackageVersion):
		self.requiredPackageVersion = forcePackageVersion(requiredPackageVersion)
	
	def getRequiredAction(self):
		return self.requiredAction
	
	def setRequiredAction(self, requiredAction):
		self.requiredAction = forceActionRequest(requiredAction)
	
	def getRequiredInstallationStatus(self):
		return self.requiredInstallationStatus
	
	def setRequiredInstallationStatus(self, requiredInstallationStatus):
		self.requiredInstallationStatus = forceInstallationStatus(requiredInstallationStatus)
	
	def getRequirementType(self):
		return self.requirementType
	
	def setRequirementType(self, requirementType):
		self.requirementType = forceRequirementType(requirementType)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductDependency'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductDependency.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', productVersion '%s', packageVersion '%s', productAction '%s', requiredProductId '%s'>" \
			% (self.getType(), self.productId, self.productVersion, self.packageVersion, self.productAction, self.requiredProductId)
	
Relationship.subClasses['ProductDependency'] = ProductDependency

class ProductOnDepot(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productOnDepot'
	
	def __init__(self, productId, productType, productVersion, packageVersion, depotId, locked=None):
		self.locked = None
		self.setProductId(productId)
		self.setProductType(productType)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setDepotId(depotId)
		if not locked is None:
			self.setLocked(locked)
	
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.locked is None:
			self.setLocked(False)
	
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getProductType(self):
		return self.productType
	
	def setProductType(self, productType):
		self.productType = forceProductType(productType)
	
	def getProductVersion(self):
		return self.productVersion
	
	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)
	
	def getPackageVersion(self):
		return self.packageVersion
	
	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)
	
	def getDepotId(self):
		return self.depotId
	
	def setDepotId(self, depotId):
		self.depotId = forceHostId(depotId)
	
	def getLocked(self):
		return self.locked
	
	def setLocked(self, locked):
		self.locked = forceBool(locked)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductOnDepot'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductOnDepot.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', depotId '%s'>" \
			% (self.getType(), self.productId, self.depotId)
	
Relationship.subClasses['ProductOnDepot'] = ProductOnDepot


class ProductOnClient(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productOnClient'
	
	def __init__(self, productId, productType, clientId, installationStatus=None, actionRequest=None, actionProgress=None, productVersion=None, packageVersion=None, lastStateChange=None):
		self.installationStatus = None
		self.actionRequest = None
		self.actionProgress = None
		self.productVersion = None
		self.packageVersion = None
		self.lastStateChange = None
		self.setProductId(productId)
		self.setProductType(productType)
		self.setClientId(clientId)
		if not installationStatus is None:
			self.setInstallationStatus(installationStatus)
		if not actionRequest is None:
			self.setActionRequest(actionRequest)
		if not actionProgress is None:
			self.setActionProgress(actionProgress)
		if not productVersion is None:
			self.setProductVersion(productVersion)
		if not packageVersion is None:
			self.setPackageVersion(packageVersion)
		if not lastStateChange is None:
			self.setLastStateChange(lastStateChange)
	
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.installationStatus is None:
			self.setInstallationStatus('not_installed')
		if self.actionRequest is None:
			self.setActionRequest('none')
		if self.lastStateChange is None:
			self.setLastStateChange(timestamp())
		
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getProductType(self):
		return self.productType
	
	def setProductType(self, productType):
		self.productType = forceProductType(productType)
	
	def getClientId(self):
		return self.clientId
	
	def setClientId(self, clientId):
		self.clientId = forceHostId(clientId)
	
	def getInstallationStatus(self):
		return self.installationStatus
	
	def setInstallationStatus(self, installationStatus):
		self.installationStatus = forceInstallationStatus(installationStatus)
	
	def getActionRequest(self):
		return self.actionRequest
	
	def setActionRequest(self, actionRequest):
		self.actionRequest = forceActionRequest(actionRequest)
	
	def getActionProgress(self):
		return self.actionProgress
	
	def setActionProgress(self, actionProgress):
		self.actionProgress = forceActionProgress(actionProgress)
	
	def getProductVersion(self):
		return self.productVersion
	
	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)
		
	def getPackageVersion(self):
		return self.packageVersion
	
	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)
	
	def getLastStateChange(self):
		return self.lastStateChange
	
	def setLastStateChange(self, lastStateChange):
		self.lastStateChange = forceOpsiTimestamp(lastStateChange)
		
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductOnClient'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s clientId '%s', productId '%s'>" \
			% (self.getType(), self.clientId, self.productId)
	
Relationship.subClasses['ProductOnClient'] = ProductOnClient

class ProductPropertyState(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productPropertyState'
	
	def __init__(self, productId, propertyId, objectId, values=None):
		self.values = None
		self.setProductId(productId)
		self.setPropertyId(propertyId)
		self.setObjectId(objectId)
		if not values is None:
			self.setValues(values)
	
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.values is None:
			self.setValues([])
	
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getObjectId(self):
		return self.objectId
	
	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)
	
	def getPropertyId(self):
		return self.propertyId
	
	def setPropertyId(self, propertyId):
		self.propertyId = forceUnicodeLower(propertyId)
	
	def getValues(self):
		return self.values
	
	def setValues(self, values):
		self.values = forceList(values)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductPropertyState'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductPropertyState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', objectId '%s', propertyId '%s'>" \
			% (self.getType(), self.productId, self.objectId, self.propertyId)
	
Relationship.subClasses['ProductPropertyState'] = ProductPropertyState

class Group(Object):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['groupId']
	backendMethodPrefix = 'group'
	
	def __init__(self, id, description=None, notes=None, parentGroupId=None):
		Object.__init__(self, id, description, notes)
		self.parentGroupId = None
		self.setId(id)
		if not parentGroupId is None:
			self.setParentGroupId(parentGroupId)
	
	def setDefaults(self):
		Object.setDefaults(self)
	
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceGroupId(id)
	
	def getParentGroupId(self):
		return self.parentGroupId
	
	def setParentGroupId(self, parentGroupId):
		self.parentGroupId = forceGroupId(parentGroupId)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Group'
		return Object.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Group.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', parentGroupId '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.parentGroupId)
	
Object.subClasses['Group'] = Group

class HostGroup(Group):
	subClasses = {}
	
	def __init__(self, id, description=None, notes=None, parentGroupId=None):
		Group.__init__(self, id, description, notes, parentGroupId)
	
	def setDefaults(self):
		Group.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'HostGroup'
		return Group.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return HostGroup.fromHash(json.loads(jsonString))
	
Group.subClasses['HostGroup'] = HostGroup

class ObjectToGroup(Relationship):
	subClasses = {}
	
	def __init__(self, groupId, objectId):
		self.setGroupId(groupId)
		self.setObjectId(objectId)
	
	def setDefaults(self):
		Relationship.setDefaults(self)
	
	def getGroupId(self):
		return self.groupId
	
	def setGroupId(self, groupId):
		self.groupId = forceGroupId(groupId)
	
	def getObjectId(self):
		return self.objectId
	
	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ObjectToGroup'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ObjectToGroup.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s groupId '%s', objectId '%s'>" \
			% (self.getType(), self.groupId, self.objectId)
	
Relationship.subClasses['ObjectToGroup'] = ObjectToGroup


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -   License management                                                                        -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class LicenseContract(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['licenseContractId']
	backendMethodPrefix = 'licenseContract'
	
	def __init__(self, id, description=None, notes=None, partner=None, conclusionDate=None, notificationDate=None, expirationDate=None):
		self.description = None
		self.notes = None
		self.partner = None
		self.conclusionDate = None
		self.notificationDate = None
		self.expirationDate = None
		self.setId(id)
		if not description is None:
			self.setDescription(description)
		if not notes is None:
			self.setNotes(notes)
		if not partner is None:
			self.setPartner(partner)
		if not conclusionDate is None:
			self.setConclusionDate(conclusionDate)
		if not notificationDate is None:
			self.setNotificationDate(notificationDate)
		if not conclusionDate is None:
			self.setExpirationDate(expirationDate)
	
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.notes is None:
			self.setNotes(u"")
		if self.partner is None:
			self.setPartner(u"")
		if self.conclusionDate is None:
			self.setConclusionDate(timestamp())
		if self.notificationDate is None:
			self.setNotificationDate('0000-00-00 00:00:00')
		if self.expirationDate is None:
			self.setExpirationDate('0000-00-00 00:00:00')
		
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceLicenseContractId(id)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getNotes(self):
		return self.notes
	
	def setNotes(self, notes):
		self.notes = forceUnicode(notes)
	
	def getPartner(self):
		return self.partner
	
	def setPartner(self, partner):
		self.partner = forceUnicode(partner)
	
	def getConclusionDate(self):
		return self.conclusionDate
	
	def setConclusionDate(self, conclusionDate):
		self.conclusionDate = forceOpsiTimestamp(conclusionDate)
	
	def getNotificationDate(self):
		return self.notificationDate
	
	def setNotificationDate(self, notificationDate):
		self.notificationDate = forceOpsiTimestamp(notificationDate)
	
	def getExpirationDate(self):
		return self.expirationDate
	
	def setExpirationDate(self, expirationDate):
		self.expirationDate = forceOpsiTimestamp(expirationDate)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'LicenseContract'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return LicenseContract.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s'>" \
			% (self.getType(), self.id, self.description)
	
Entity.subClasses['LicenseContract'] = LicenseContract

class SoftwareLicense(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['softwareLicenseId']
	backendMethodPrefix = 'softwareLicense'
	
	def __init__(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		self.maxInstallations = None
		self.boundToHost = None
		self.expirationDate = None
		self.setId(id)
		self.setLicenseContractId(licenseContractId)
		if not maxInstallations is None:
			self.setMaxInstallations(maxInstallations)
		if not boundToHost is None:
			self.setBoundToHost(boundToHost)
		if not expirationDate is None:
			self.setExpirationDate(expirationDate)
		
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.maxInstallations is None:
			self.setMaxInstallations(1)
		if self.expirationDate is None:
			self.setExpirationDate('0000-00-00 00:00:00')
		
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceSoftwareLicenseId(id)
	
	def getLicenseContractId(self):
		return self.licenseContractId
	
	def setLicenseContractId(self, licenseContractId):
		self.licenseContractId = forceLicenseContractId(licenseContractId)
	
	def getMaxInstallations(self):
		return self.maxInstallations
	
	def setMaxInstallations(self, maxInstallations):
		self.maxInstallations = forceUnsignedInt(maxInstallations)
	
	def getBoundToHost(self):
		return self.boundToHost
	
	def setBoundToHost(self, boundToHost):
		self.boundToHost = forceHostId(boundToHost)
	
	def getExpirationDate(self):
		return self.expirationDate
	
	def setExpirationDate(self, expirationDate):
		self.expirationDate = forceOpsiTimestamp(expirationDate)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'SoftwareLicense'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return SoftwareLicense.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', licenseContractId '%s'>" \
			% (self.getType(), self.id, self.licenseContractId)
	
Entity.subClasses['LicenseContract'] = LicenseContract

class RetailSoftwareLicense(SoftwareLicense):
	subClasses = {}
	
	def __init__(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, maxInstallations, boundToHost, expirationDate)
		
	def setDefaults(self):
		SoftwareLicense.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'RetailSoftwareLicense'
		return SoftwareLicense.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return RetailSoftwareLicense.fromHash(json.loads(jsonString))
	
SoftwareLicense.subClasses['RetailSoftwareLicense'] = RetailSoftwareLicense

class OEMSoftwareLicense(SoftwareLicense):
	subClasses = {}
	
	def __init__(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, 1, boundToHost, expirationDate)
		
	def setDefaults(self):
		SoftwareLicense.setDefaults(self)
	
	def setMaxInstallations(self, maxInstallations):
		maxInstallations = forceUnsignedInt(maxInstallations)
		if (maxInstallations > 1):
			raise BackendBadValueError(u"OEM software license max installations can only be set to 1")
		self.maxInstallations = maxInstallations
	
	def setBoundToHost(self, boundToHost):
		self.boundToHost = forceHostId(boundToHost)
		if not self.boundToHost:
			raise BackendBadValueError("OEM software license requires boundToHost value")
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OEMSoftwareLicense'
		return SoftwareLicense.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OEMSoftwareLicense.fromHash(json.loads(jsonString))
	
SoftwareLicense.subClasses['OEMSoftwareLicense'] = OEMSoftwareLicense

class VolumeSoftwareLicense(SoftwareLicense):
	subClasses = {}
	
	def __init__(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, maxInstallations, boundToHost, expirationDate)
	
	def setDefaults(self):
		SoftwareLicense.setDefaults(self)
		if self.maxInstallations is None:
			self.setMaxInstallations(1)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'VolumeSoftwareLicense'
		return SoftwareLicense.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return VolumeSoftwareLicense.fromHash(json.loads(jsonString))
	
SoftwareLicense.subClasses['VolumeSoftwareLicense'] = VolumeSoftwareLicense

class ConcurrentSoftwareLicense(SoftwareLicense):
	subClasses = {}
	
	def __init__(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, maxInstallations, boundToHost, expirationDate)
	
	def setDefaults(self):
		SoftwareLicense.setDefaults(self)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ConcurrentSoftwareLicense'
		return SoftwareLicense.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ConcurrentSoftwareLicense.fromHash(json.loads(jsonString))
	
SoftwareLicense.subClasses['ConcurrentSoftwareLicense'] = ConcurrentSoftwareLicense

class LicensePool(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['licensePoolId']
	backendMethodPrefix = 'licensePool'
	
	def __init__(self, id, description=None, productIds=None, windowsSoftwareIds=None):
		self.description = None
		self.productIds = None
		self.windowsSoftwareIds = None
		self.setId(id)
		if not description is None:
			self.setDescription(description)
		if not productIds is None:
			self.setProductIds(productIds)
		if not windowsSoftwareIds is None:
			self.setWindowsSoftwareIds(windowsSoftwareIds)
		
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.productIds is None:
			self.setProductIds([])
		if self.windowsSoftwareIds is None:
			self.setWindowsSoftwareIds([])
		
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceLicensePoolId(id)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getProductIds(self):
		return self.productIds
	
	def setProductIds(self, productIds):
		self.productIds = forceProductIdList(productIds)
	
	def getWindowsSoftwareIds(self):
		return self.windowsSoftwareIds
	
	def setWindowsSoftwareIds(self, windowsSoftwareIds):
		self.windowsSoftwareIds = forceUnicodeList(windowsSoftwareIds)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'LicensePool'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return LicensePool.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s'>" \
			% (self.getType(), self.id, self.description)
	
Entity.subClasses['LicensePool'] = LicensePool

class SoftwareLicenseToLicensePool(Relationship):
	subClasses = {}
	
	def __init__(self, softwareLicenseId, licensePoolId, licenseKey = None):
		self.licenseKey = None
		self.setSoftwareLicenseId(softwareLicenseId)
		self.setLicensePoolId(licensePoolId)
		if not licenseKey is None:
			self.setLicenseKey(licenseKey)
		
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.licenseKey is None:
			self.setLicenseKey(u'')
	
	def getSoftwareLicenseId(self):
		return self.softwareLicenseId
	
	def setSoftwareLicenseId(self, softwareLicenseId):
		self.softwareLicenseId = forceSoftwareLicenseId(softwareLicenseId)
	
	def getLicensePoolId(self):
		return self.licensePoolId
	
	def setLicensePoolId(self, licensePoolId):
		self.licensePoolId = forceLicensePoolId(licensePoolId)
	
	def getLicenseKey(self):
		return self.licenseKey
	
	def setLicenseKey(self, licenseKey):
		self.licenseKey = forceUnicodeLower(licenseKey)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'SoftwareLicenseToLicensePool'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return SoftwareLicenseToLicensePool.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s softwareLicenseId '%s', licensePoolId '%s'>" \
			% (self.getType(), self.softwareLicenseId, self.licensePoolId)
	
Relationship.subClasses['SoftwareLicenseToLicensePool'] = SoftwareLicenseToLicensePool

class LicenseOnClient(Relationship):
	subClasses = {}
	backendMethodPrefix = 'licenseOnClient'
	
	def __init__(self, softwareLicenseId, licensePoolId, clientId, licenseKey=None, notes=None):
		self.licenseKey = None
		self.notes = None
		self.setSoftwareLicenseId(softwareLicenseId)
		self.setLicensePoolId(licensePoolId)
		self.setClientId(clientId)
		if not licenseKey is None:
			self.setLicenseKey(licenseKey)
		if not notes is None:
			self.setNotes(notes)
		
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.licenseKey is None:
			self.setLicenseKey(u'')
		if self.notes is None:
			self.setNotes(u'')
		
	def getSoftwareLicenseId(self):
		return self.softwareLicenseId
	
	def setSoftwareLicenseId(self, softwareLicenseId):
		self.softwareLicenseId = forceSoftwareLicenseId(softwareLicenseId)
	
	def getLicensePoolId(self):
		return self.licensePoolId
	
	def setLicensePoolId(self, licensePoolId):
		self.licensePoolId = forceLicensePoolId(licensePoolId)
	
	def getClientId(self):
		return self.clientId
	
	def setClientId(self, clientId):
		self.clientId = forceHostId(clientId)
	
	def getLicenseKey(self):
		return self.licenseKey
	
	def setLicenseKey(self, licenseKey):
		self.licenseKey = forceUnicodeLower(licenseKey)
	
	def getNotes(self):
		return self.notes
	
	def setNotes(self, notes):
		self.notes = forceUnicode(notes)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'LicenseOnClient'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return LicenseOnClient.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s softwareLicenseId '%s', licensePoolId '%s', clientId '%s'>" \
			% (self.getType(), self.softwareLicenseId, self.licensePoolId, self.clientId)
	
Relationship.subClasses['LicenseOnClient'] = LicenseOnClient




class AuditSoftware(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes
	backendMethodPrefix = 'auditSoftware'
	
	def __init__(self, softwareId, displayName, displayVersion, uninstallString=None, binaryName=None, installSize=None):
		self.uninstallString = None
		self.binaryName = None
		self.installSize = None
		self.setSoftwareId(softwareId)
		self.setDisplayName(displayName)
		self.setDisplayVersion(displayVersion)
		if not uninstallString is None:
			self.setUninstallString(uninstallString)
		if not binaryName is None:
			self.setBinaryName(binaryName)
		if not installSize is None:
			self.setInstallSize(installSize)
		
	def setDefaults(self):
		Entity.setDefaults(self)
		if self.uninstallString is None:
			self.setUninstallString(u"")
		if self.binaryName is None:
			self.setBinaryName(u"")
		if self.installSize is None:
			self.setInstallSize(0)
		
	def getSoftwareId(self):
		return self.softwareId
	
	def setSoftwareId(self, softwareId):
		self.softwareId = forceUnicodeLower(softwareId)
	
	def getDisplayName(self):
		return self.displayName
	
	def setDisplayName(self, displayName):
		self.displayName = forceUnicode(displayName)
	
	def getDisplayVersion(self):
		return self.displayVersion
	
	def setDisplayVersion(self, displayVersion):
		self.displayVersion = forceUnicode(displayVersion)
	
	def getUninstallString(self):
		return self.uninstallString
	
	def setUninstallString(self, uninstallString):
		self.uninstallString = forceUnicode(uninstallString)
	
	def getBinaryName(self):
		return self.binaryName
	
	def setBinaryName(self, binaryName):
		self.binaryName = forceUnicode(binaryName)
	
	def getInstallSize(self):
		return self.installSize
	
	def setInstallSize(self, installSize):
		self.installSize = forceInt(installSize)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'AuditSoftware'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return AuditSoftware.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s  softwareId '%s', displayName '%s', displayVersion '%s'>" \
			% (self.getType(), self.softwareId, self.displayName, self.displayVersion)
	
Entity.subClasses['AuditSoftware'] = AuditSoftware


class AuditSoftwareOnClient(Relationship):
	subClasses = {}
	backendMethodPrefix = 'auditSoftwareOnClient'
	
	def __init__(self, softwareId, displayName, displayVersion, clientId, firstseen=None, lastseen=None, state=None, usageFrequency=None, lastUsed=None):
		self.firstseen = None
		self.lastseen = None
		self.state = None
		self.usageFrequency = None
		self.lastUsed = None
		self.setSoftwareId(softwareId)
		self.setDisplayName(displayName)
		self.setDisplayVersion(displayVersion)
		self.setClientId(clientId)
		if not firstseen is None:
			self.setFirstseen(firstseen)
		if not lastseen is None:
			self.setLastseen(lastseen)
		if not state is None:
			self.setState(state)
		if not usageFrequency is None:
			self.setUsageFrequency(usageFrequency)
		if not lastUsed is None:
			self.setLastUsed(lastUsed)
		
	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.firstseen is None:
			self.setFirstseen(timestamp())
		if self.lastseen is None:
			self.setLastseen(timestamp())
		if self.state is None:
			self.setState(1)
		if self.usageFrequency is None:
			self.setUsageFrequency(-1)
		if self.lastUsed is None:
			self.setLastUsed('0000-00-00 00:00:00')
		
	def getSoftwareId(self):
		return self.softwareId
	
	def setSoftwareId(self, softwareId):
		self.softwareId = forceUnicodeLower(softwareId)
	
	def getDisplayName(self):
		return self.displayName
	
	def setDisplayName(self, displayName):
		self.displayName = forceUnicode(displayName)
	
	def getDisplayVersion(self):
		return self.displayVersion
	
	def setDisplayVersion(self, displayVersion):
		self.displayVersion = forceUnicode(displayVersion)
	
	def getClientId(self):
		return self.clientId
	
	def setClientId(self, clientId):
		self.clientId = forceHostId(clientId)
	
	def getFirstseen(self):
		return self.firstseen
	
	def setFirstseen(self, firstseen):
		self.firstseen = forceOpsiTimestamp(firstseen)
	
	def getLastseen(self):
		return self.firstseen
	
	def setLastseen(self, lastseen):
		self.lastseen = forceOpsiTimestamp(lastseen)
	
	def getState(self):
		return self.state
	
	def setState(self, state):
		self.state = forceAuditState(state)
	
	def getUsageFrequency(self):
		return self.usageFrequency
	
	def setUsageFrequency(self, usageFrequency):
		self.usageFrequency = forceInt(usageFrequency)
	
	def getLastUsed(self):
		return self.lastUsed
	
	def setLastUsed(self, lastUsed):
		self.lastUsed = forceOpsiTimestamp(lastUsed)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'AuditSoftwareOnClient'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return AuditSoftwareOnClient.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s softwareId '%s', displayName '%s', displayVersion '%s', clientId '%s'>" \
			% (self.getType(), self.softwareId, self.displayName, self.displayVersion, self.clientId)
	
Relationship.subClasses['AuditSoftwareOnClient'] = AuditSoftwareOnClient











