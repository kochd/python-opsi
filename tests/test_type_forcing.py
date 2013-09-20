#!/usr/bin/env python
#-*- coding: utf-8 -*-
import datetime
import time
import unittest

from OPSI.Object import OpsiClient, Host
from OPSI.Types import (forceObjectClass, forceUnicode, forceUnicodeList,
	forceList, forceBool, forceBoolList, forceInt, forceOct, forceIPAddress,
	forceOpsiTimestamp, forceHardwareAddress, forceHostId, forceNetworkAddress,
	forceUrl, forceProductId, forcePackageVersion,forceFilename, forceTime,
	forceProductVersion, forceOpsiHostKey,forceInstallationStatus,
	forceActionRequest, forceActionProgress,forceLanguageCode, forceIntList,
	forceArchitecture, forceEmailAddress, forceUnicodeLowerList,
	forceProductType)


class ForceObjectClassJSONTestCase(unittest.TestCase):
	def setUp(self):
		self.object = OpsiClient(
			id='test1.uib.local',
			description='Test client 1',
			notes='Notes ...',
			hardwareAddress='00:01:02:03:04:05',
			ipAddress='192.168.1.100',
			lastSeen='2009-01-01 00:00:00',
			opsiHostKey='45656789789012789012345612340123'
		)

		self.json = self.object.toJson()

	def tearDown(self):
		del self.json
		del self.object

	def testForceObjectClassToHostFromJSON(self):
		self.assertTrue(isinstance(forceObjectClass(self.json, Host), Host))

	def testForceObjectClassToOpsiClientFromJSON(self):
		self.assertTrue(isinstance(forceObjectClass(self.json, OpsiClient), OpsiClient))


class ForceObjectClassHashTestCase(unittest.TestCase):
	def setUp(self):
		self.object = OpsiClient(
			id='test1.uib.local',
			description='Test client 1',
			notes='Notes ...',
			hardwareAddress='00:01:02:03:04:05',
			ipAddress='192.168.1.100',
			lastSeen='2009-01-01 00:00:00',
			opsiHostKey='45656789789012789012345612340123'
		)

		self.hash = self.object.toHash()

	def tearDown(self):
		del self.hash
		del self.object

	def testForceObjectClassToHostFromHash(self):
		self.assertTrue(isinstance(forceObjectClass(self.hash, Host), Host))

	def testForceObjectClassToOpsiClientFromHash(self):
		self.assertTrue(isinstance(forceObjectClass(self.hash, OpsiClient), OpsiClient))


class ForceListTestCase(unittest.TestCase):
	def testForceListCreatesAListIfOnlyOneObjectIsGiven(self):
		self.assertEquals(forceList('x'), ['x'])


class ForceUnicodeTestCase(unittest.TestCase):
	def testForcingResultsInUnicode(self):
		self.assertTrue(type(forceUnicode('x')) is unicode)


class ForceUnicodeListTestCase(unittest.TestCase):
	def testForcingResultsInUnicode(self):
		for i in forceUnicodeList([None, 1, 'x', u'y']):
			self.assertTrue(type(i) is unicode)


class ForceUnicodeLowerListTestCase(unittest.TestCase):
	def testForcingResultsInLowercase(self):
		self.assertEqual(forceUnicodeLowerList(['X', u'YES']), ['x', 'yes'])

	def testForcingResultsInUnicode(self):
		for i in forceUnicodeLowerList([None, 1, 'X', u'y']):
			self.assertTrue(type(i) is unicode)


class ForceBoolTestCase(unittest.TestCase):
	"""
	Testing if forceBool works. Always should work case-insensitive.
	"""
	def testOnOff(self):
		self.assertTrue(forceBool('on'))
		self.assertFalse(forceBool('OFF'))

	def testYesNo(self):
		self.assertTrue(forceBool('YeS'))
		self.assertFalse(forceBool('no'))

	def testOneZero(self):
		self.assertTrue(forceBool(1))
		self.assertTrue(forceBool('1'))
		self.assertFalse(forceBool(0))
		self.assertFalse(forceBool('0'))

	def testXMarksTheSpot(self):
		self.assertTrue(forceBool(u'x'))

	def testBoolTypes(self):
		self.assertTrue(forceBool(True))
		self.assertFalse(forceBool(False))


class ForceBoolListTestCase(unittest.TestCase):
	def testPositiveList(self):
		for i in forceBoolList([1, 'yes', 'on', '1', True]):
			self.assertTrue(i)

	def testMethod(self):
		for i in forceBoolList([None, 'no', 'false', '0', False]):
			self.assertFalse(i)


class ForceIntTestCase(unittest.TestCase):
	def testWithString(self):
		self.assertEquals(forceInt('100'), 100)

	def testWithNegativeValueInString(self):
		self.assertEquals(forceInt('-100'), -100)

	def testWithLongValue(self):
		self.assertEquals(forceInt(long(1000000000000000)), 1000000000000000)

	def testRaisingValueError(self):
		self.assertRaises(ValueError, forceInt, 'abc')


class ForceIntListTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertEquals(forceIntList(['100', 1, u'2']), [100, 1 , 2])


class ForceOctTestCase(unittest.TestCase):
	def testForcingDoesNotChangeValue(self):
		self.assertEquals(forceOct(0666), 0666)

	def testForcingString(self):
		self.assertEquals(forceOct('666'), 0666)

	def testForcingStringWithLeadingZero(self):
		self.assertEquals(forceOct('0666'), 0666)

	def testRaisingErrors(self):
		self.assertRaises(ValueError, forceOct, 'abc')


class ForceOpsiTimeStampTestCase(unittest.TestCase):
	def testForcingReturnsString(self):
		self.assertEquals(forceOpsiTimestamp('20000202111213'), u'2000-02-02 11:12:13')

	def testResultIsUnicode(self):
		self.assertTrue(type(forceOpsiTimestamp('2000-02-02 11:12:13')) is unicode)

	def testRaisingErrorsOnWrongInput(self):
		self.assertRaises(ValueError, forceOpsiTimestamp, 'abc')

	def testForcingWithAnEmptyValue(self):
		self.assertEqual(forceOpsiTimestamp(None), '0000-00-00 00:00:00')

	def testForcingWithDatetime(self):
		self.assertEqual(forceOpsiTimestamp(datetime.datetime(2013, 9, 11, 10, 54, 23)), '2013-09-11 10:54:23')


class ForceHostIdTestCase(unittest.TestCase):
	def testForcingWithValidId(self):
		self.assertEquals(forceHostId(u'client.uib.local'), u'client.uib.local')
		self.assertTrue(forceHostId(u'client.uib.local'), u'client.uib.local')

	def testInvalidHOstIdsRaiseExceptions(self):
		self.assertRaises(ValueError, forceHostId, 'abc')
		self.assertRaises(ValueError, forceHostId, 'abc.def')
		self.assertRaises(ValueError, forceHostId, '.uib.local')
		self.assertRaises(ValueError, forceHostId, 'abc.uib.x')


class ForceHardwareAddressTestCase(unittest.TestCase):
	def testForcingReturnsAddressSeperatedByColons(self):
		self.assertEquals(forceHardwareAddress('12345678ABCD'), u'12:34:56:78:ab:cd')
		self.assertEquals(forceHardwareAddress('12:34:56:78:ab:cd'), u'12:34:56:78:ab:cd')

	def testForcingReturnsLowercaseLetters(self):
		self.assertEquals(forceHardwareAddress('12-34-56-78-Ab-cD'), u'12:34:56:78:ab:cd')
		self.assertEquals(forceHardwareAddress('12-34-56:78AB-CD'), u'12:34:56:78:ab:cd')

	def testForcingResultsInUnicode(self):
		self.assertTrue(type(forceHardwareAddress('12345678ABCD')) is unicode)

	def testForcingInvalidAddressesRaiseExceptions(self):
		self.assertRaises(ValueError, forceHardwareAddress, '12345678abc')
		self.assertRaises(ValueError, forceHardwareAddress, '12345678abcdef')
		self.assertRaises(ValueError, forceHardwareAddress, '1-2-3-4-5-6-7')
		self.assertRaises(ValueError, forceHardwareAddress, None)
		self.assertRaises(ValueError, forceHardwareAddress, True)


class ForceIPAdressTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertEquals(forceIPAddress('192.168.101.1'), u'192.168.101.1')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceIPAddress('1.1.1.1')) is unicode)

	def testForcingWithInvalidAddressesRaisesExceptions(self):
		self.assertRaises(ValueError, forceIPAddress, '1922.1.1.1')
		self.assertRaises(ValueError, forceIPAddress, None)
		self.assertRaises(ValueError, forceIPAddress, True)
		self.assertRaises(ValueError, forceIPAddress, '1.1.1.1.')
		self.assertRaises(ValueError, forceIPAddress, '2.2.2.2.2')
		self.assertRaises(ValueError, forceIPAddress, 'a.2.3.4')


class ForceNetworkAddressTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertEquals(forceNetworkAddress('192.168.0.0/16'), u'192.168.0.0/16')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceNetworkAddress('10.10.10.10/32')) is unicode)

	def testForcingWithInvalidAddressesRaisesExceptions(self):
		self.assertRaises(ValueError, forceNetworkAddress, '192.168.101.1')
		self.assertRaises(ValueError, forceNetworkAddress, '192.1.1.1/40')
		self.assertRaises(ValueError, forceNetworkAddress, None)
		self.assertRaises(ValueError, forceNetworkAddress, True)
		self.assertRaises(ValueError, forceNetworkAddress, '10.10.1/24')
		self.assertRaises(ValueError, forceNetworkAddress, 'a.2.3.4/0')


class ForceUrlTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertTrue(forceUrl('file:///'), 'file:///')
		self.assertTrue(forceUrl('file:///path/to/file'), 'file:///path/to/file')
		self.assertTrue(forceUrl('smb://server/path'), 'smb://server/path')
		self.assertTrue(forceUrl('https://x:y@server.domain.tld:4447/resource'), 'https://x:y@server.domain.tld:4447/resource')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceUrl('file:///')) is unicode)
		self.assertTrue(type(forceUrl('file:///path/to/file')) is unicode)
		self.assertTrue(type(forceUrl('smb://server/path')) is unicode)
		self.assertTrue(type(forceUrl('https://x:y@server.domain.tld:4447/resource')) is unicode)

	def testForcingWithInvalidURLsRaisesExceptions(self):
		self.assertRaises(ValueError, forceUrl, 'abc')
		self.assertRaises(ValueError, forceUrl, '/abc')
		self.assertRaises(ValueError, forceUrl, 'http//server')
		self.assertRaises(ValueError, forceUrl, 1)
		self.assertRaises(ValueError, forceUrl, True)
		self.assertRaises(ValueError, forceUrl, None)


class ForceOpsiHostKeyTestCase(unittest.TestCase):
	def testForcingReturnsLowercase(self):
		self.assertEquals(forceOpsiHostKey('abCdeF78901234567890123456789012'), 'abcdef78901234567890123456789012')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceOpsiHostKey('12345678901234567890123456789012')) is unicode)

	def testForcingWithInvalidHostKeysRaisesExceptions(self):
		self.assertRaises(ValueError, forceOpsiHostKey, 'abCdeF7890123456789012345678901')
		self.assertRaises(ValueError, forceOpsiHostKey, 'abCdeF78901234567890123456789012b')
		self.assertRaises(ValueError, forceOpsiHostKey, 'GbCdeF78901234567890123456789012')


class ForceProductVersionTestCase(unittest.TestCase):
	def testForcing(self):
		forceProductVersion('1.0') == '1.0'

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceProductVersion('1.0')) is unicode)

	def testProductVersionDoesNotContainUppercase(self):
		self.assertRaises(ValueError, forceProductVersion, 'A1.0')


class ForcePackageVersionTestCase(unittest.TestCase):
	def testMethod(self):
		self.assertEquals(forcePackageVersion(1), '1')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forcePackageVersion('8')) is unicode)

	def testPackageVersionDoesNotContainUppercase(self):
		self.assertRaises(ValueError, forcePackageVersion, 'A')


class ForceProductIdTestCase(unittest.TestCase):
	def testMethod(self):
		self.assertEquals(forceProductId('testProduct1'), 'testproduct1')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceProductId('test-Product-1')) is unicode)


	def testForcingWithInvalidProductIdRaisesExceptions(self):
		self.assertRaises(ValueError, forceProductId, u'äöü')
		self.assertRaises(ValueError, forceProductId, 'product test')


class ForceFilenameTestCase(unittest.TestCase):
	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceFilename('/tmp/test.txt')) is unicode)

	def testForcingFilename(self):
		self.assertEquals(forceFilename('c:\\tmp\\test.txt'), u'c:\\tmp\\test.txt')


class ForceInstallationStatusTestCase(unittest.TestCase):
	def testForcingAcceptsOnlyValidStatus(self):
		self.assertEquals(forceInstallationStatus('installed'), 'installed')
		self.assertEquals(forceInstallationStatus('not_installed'), 'not_installed')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceInstallationStatus('installed')) is unicode)
		self.assertTrue(type(forceInstallationStatus('not_installed')) is unicode)

	def testForcingWithInvalidStatusRaisesExceptions(self):
		self.assertRaises(ValueError, forceInstallationStatus, 'none')
		self.assertRaises(ValueError, forceInstallationStatus, 'abc')


class ForceActionRequestTestCase(unittest.TestCase):
	def testForcingWithInvalidStatusRaisesExceptions(self):
		self.assertRaises(ValueError, forceActionRequest, 'installed')

	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceActionRequest('setup')) is unicode)

	def testForcingReturnsLowercase(self):
		self.assertEquals(forceActionRequest('setup'), str('setup').lower())
		self.assertEquals(forceActionRequest('uninstall'), str('uninstall').lower())
		self.assertEquals(forceActionRequest('update'), str('update').lower())
		self.assertEquals(forceActionRequest('once'), str('once').lower())
		self.assertEquals(forceActionRequest('always'), str('always').lower())
		self.assertEquals(forceActionRequest('none'), str('none').lower())
		self.assertEquals(forceActionRequest(None), str(None).lower())


class ForceActionProgressTestCase(unittest.TestCase):
	def testForcingReturnsUnicode(self):
		self.assertTrue(type(forceActionProgress('installing 50%')) is unicode)

	def testForcing(self):
		self.assertEquals(forceActionProgress('installing 50%'), u'installing 50%')


class ForceLanguageCodeTestCase(unittest.TestCase):
	def testCasingGetsAdjusted(self):
		self.assertEquals(forceLanguageCode('xx-xxxx-xx'), u'xx-Xxxx-XX')
		self.assertEquals(forceLanguageCode('yy_yy'), u'yy-YY')
		self.assertEquals(forceLanguageCode('zz_ZZZZ'), u'zz-Zzzz')

	def testForcing(self):
		self.assertEquals(forceLanguageCode('dE'), u'de')
		self.assertEquals(forceLanguageCode('en-us'), u'en-US')

	def testForcingWithWrongCodeSetupRaisesExceptions(self):
		self.assertRaises(ValueError, forceLanguageCode, 'de-DEU')


class ForceArchitectureTestCase(unittest.TestCase):
	def testForcingReturnsLowercase(self):
		self.assertEquals(forceArchitecture('X86'), u'x86')
		self.assertEquals(forceArchitecture('X64'), u'x64')


class ForceTimeTestCase(unittest.TestCase):
	def testForcingFailsWithInvalidTime(self):
		self.assertRaises(ValueError, forceTime, 'Hello World!')

	def testForcingWorksWithVariousTypes(self):
		forceTime(time.time())
		forceTime(time.localtime())


class ForceEmailAddressTestCase(unittest.TestCase):
	def testForcingRequiresValidMailAddress(self):
		self.assertRaises(ValueError, forceEmailAddress, 'infouib.de')

	def testForcing(self):
		self.assertEquals(forceEmailAddress('info@uib.de'), u'info@uib.de')


class ForceProductTypeTestCase(unittest.TestCase):
    def testRaisingExceptionOnUnknownType(self):
        self.assertRaises(ValueError, forceProductType, 'TrolololoProduct')

    def testForcingToLocalbootProduct(self):
    	self.assertEquals(forceProductType('LocalBootProduct'), 'LocalbootProduct')
    	self.assertEquals(forceProductType('LOCALBOOT'), 'LocalbootProduct')

    def testForcingToNetbootProduct(self):
    	self.assertEquals(forceProductType('NetbOOtProduct'), 'NetbootProduct')
    	self.assertEquals(forceProductType('nETbOOT'), 'NetbootProduct')
