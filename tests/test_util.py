#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Util

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import random
import re
import os
import unittest

from OPSI.Util import (compareVersions, flattenSequence, formatFileSize,
    generateOpsiHostKey, getGlobalConfig, ipAddressInNetwork,
    isRegularExpressionPattern, md5sum, objectToBeautifiedText, objectToHtml,
    randomString)
from OPSI.Object import LocalbootProduct


class IPAddressInNetwork(unittest.TestCase):
    def testNetworkWithSlashIntNotation(self):
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '10.10.0.0/16'))
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '10.10.0.0/23'))
        self.assertFalse(ipAddressInNetwork('10.10.1.1', '10.10.0.0/24'))
        self.assertFalse(ipAddressInNetwork('10.10.1.1', '10.10.0.0/25'))

    def testIpAddressInNetworkWithEmptyNetworkMask(self):
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '0.0.0.0/0'))

    def testIpAddressInNetworkWithFullNetmask(self):
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '10.10.0.0/255.240.0.0'))


class ProductFactory(object):
    productVersions = ('1.0', '2', 'xxx', '3.1', '4')
    packageVersions = ('1', '2', 'y', '3', '10', 11, 22)
    licenseRequirements = (None, True, False)
    setupScripts = ('setup.ins', None)
    updateScripts = ('update.ins', None)
    uninstallScripts = ('uninstall.ins', None)
    alwaysScripts = ('always.ins', None)
    onceScripts = ('once.ins', None)
    priorities = (-100, -90, -30, 0, 30, 40, 60, 99)
    descriptions = ['Test product', 'Some product', '--------', '', None]
    advices = ('Nothing', 'Be careful', '--------', '', None)

    @classmethod
    def generateLocalbootProduct(self, index=0):
        return LocalbootProduct(
            id='product{0}'.format(index),
            productVersion=random.choice(self.productVersions),
            packageVersion=random.choice(self.packageVersions),
            name='Product {0}'.format(index),
            licenseRequired=random.choice(self.licenseRequirements),
            setupScript=random.choice(self.setupScripts),
            uninstallScript=random.choice(self.uninstallScripts),
            updateScript=random.choice(self.updateScripts),
            alwaysScript=random.choice(self.alwaysScripts),
            onceScript=random.choice(self.onceScripts),
            priority=random.choice(self.priorities),
            description=random.choice(self.descriptions),
            advice=random.choice(self.advices),
            changelog=None,
            windowsSoftwareIds=None
        )


class ObjectToHTMLTestCase(unittest.TestCase):
    def testWorkingWithManyObjectsMustNotFail(self):
        obj = [
            ProductFactory.generateLocalbootProduct(i)
            for i in range(1024)
        ]

        objectToHtml(obj, level=0)

    def testCheckingOutput(self):
        product = LocalbootProduct(
            id='htmltestproduct',
            productVersion='3.1',
            packageVersion='1',
            name='Product HTML Test',
            licenseRequired=False,
            setupScript='setup.ins',
            uninstallScript='uninstall.ins',
            updateScript='update.ins',
            alwaysScript='always.ins',
            onceScript='once.ins',
            priority=0,
            description="asdf",
            advice="lolnope",
            changelog=None,
            windowsSoftwareIds=None
        )

        expected = u'{<div style="padding-left: 3em;"><font class="json_key">"onceScript"</font>: "once.ins",<br />\n<font class="json_key">"windowsSoftwareIds"</font>: null,<br />\n<font class="json_key">"description"</font>: "asdf",<br />\n<font class="json_key">"advice"</font>: "lolnope",<br />\n<font class="json_key">"alwaysScript"</font>: "always.ins",<br />\n<font class="json_key">"updateScript"</font>: "update.ins",<br />\n<font class="json_key">"productClassIds"</font>: null,<br />\n<font class="json_key">"id"</font>: "htmltestproduct",<br />\n<font class="json_key">"licenseRequired"</font>: false,<br />\n<font class="json_key">"ident"</font>: "htmltestproduct;3.1;1",<br />\n<font class="json_key">"name"</font>: "Product&nbsp;HTML&nbsp;Test",<br />\n<font class="json_key">"changelog"</font>: null,<br />\n<font class="json_key">"customScript"</font>: null,<br />\n<font class="json_key">"uninstallScript"</font>: "uninstall.ins",<br />\n<font class="json_key">"userLoginScript"</font>: null,<br />\n<font class="json_key">"priority"</font>: 0,<br />\n<font class="json_key">"productVersion"</font>: "3.1",<br />\n<font class="json_key">"packageVersion"</font>: "1",<br />\n<font class="json_key">"type"</font>: "LocalbootProduct",<br />\n<font class="json_key">"setupScript"</font>: "setup.ins"</div>}'
        self.assertEquals(expected, objectToHtml(product))


class ObjectToBeautifiedTextTestCase(unittest.TestCase):
    def testWorkingWithManyObjectsMustNotFail(self):
        obj = [
            ProductFactory.generateLocalbootProduct(i)
            for i in range(10240)
        ]

        objectToBeautifiedText(obj)

    def testCheckingOutput(self):
        product = LocalbootProduct(
            id='htmltestproduct',
            productVersion='3.1',
            packageVersion='1',
            name='Product HTML Test',
            licenseRequired=False,
            setupScript='setup.ins',
            uninstallScript='uninstall.ins',
            updateScript='update.ins',
            alwaysScript='always.ins',
            onceScript='once.ins',
            priority=0,
            description="asdf",
            advice="lolnope",
            changelog=None,
            windowsSoftwareIds=None
        )

        expected = u"""\
[
    {
    "onceScript" : "once.ins",
    "windowsSoftwareIds" : null,
    "description" : "asdf",
    "advice" : "lolnope",
    "alwaysScript" : "always.ins",
    "updateScript" : "update.ins",
    "productClassIds" : null,
    "id" : "htmltestproduct",
    "licenseRequired" : false,
    "ident" : "htmltestproduct;3.1;1",
    "name" : "Product HTML Test",
    "changelog" : null,
    "customScript" : null,
    "uninstallScript" : "uninstall.ins",
    "userLoginScript" : null,
    "priority" : 0,
    "productVersion" : "3.1",
    "packageVersion" : "1",
    "type" : "LocalbootProduct",
    "setupScript" : "setup.ins"
    },
    {
    "onceScript" : "once.ins",
    "windowsSoftwareIds" : null,
    "description" : "asdf",
    "advice" : "lolnope",
    "alwaysScript" : "always.ins",
    "updateScript" : "update.ins",
    "productClassIds" : null,
    "id" : "htmltestproduct",
    "licenseRequired" : false,
    "ident" : "htmltestproduct;3.1;1",
    "name" : "Product HTML Test",
    "changelog" : null,
    "customScript" : null,
    "uninstallScript" : "uninstall.ins",
    "userLoginScript" : null,
    "priority" : 0,
    "productVersion" : "3.1",
    "packageVersion" : "1",
    "type" : "LocalbootProduct",
    "setupScript" : "setup.ins"
    }
]\
"""
        self.maxDiff = None
        self.assertEquals(expected, objectToBeautifiedText([product, product]))

    def testFormattingEmptyList(self):
        self.assertEquals('[\n]', objectToBeautifiedText([]))

    def testFormattingListOfEmptyLists(self):
        expected = u"""\
[
    [
    ],
    [
    ]
]\
"""
        self.assertEquals(expected, objectToBeautifiedText([[],[]]))

    def testFormattingEmptyDict(self):
        self.assertEquals('{\n}', objectToBeautifiedText({}))

        expected = u"""\
    {
    }\
"""
        self.assertEquals(expected, objectToBeautifiedText({}, level=1))


class UtilTestCase(unittest.TestCase):
    """
    General tests for functions in the Util module.
    """
    def test_flattenSequence(self):
        self.assertEqual([1, 2], flattenSequence((1, [2])))
        self.assertEqual([1, 2, 3], flattenSequence((1, [2, (3, )])))
        self.assertEqual([1, 2, 3], flattenSequence(((1, ),(2, ), 3)))

    def test_formatFileSize(self):
        self.assertEqual('123', formatFileSize(123))
        self.assertEqual('1K', formatFileSize(1234))
        self.assertEqual('1M', formatFileSize(1234567))
        self.assertEqual('1G', formatFileSize(1234567890))

    def testRandomString(self):
        self.assertEqual(10, len(randomString(10)))
        self.assertNotEqual('', randomString(1).strip())
        self.assertEqual('', randomString(0).strip())
        self.assertEqual(5*'a', randomString(5, characters='a'))

    def testGenerateOpsiHostKeyIs32CharsLong(self):
        self.assertEqual(32, len(generateOpsiHostKey()))
        self.assertEqual(32, len(generateOpsiHostKey(forcePython=True)))

    def testmd5sum(self):
        testFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'dhcpd', 'dhcpd_1.conf'
        )

        self.assertEqual('5f345ca76574c528903c1022b05acb4c', md5sum(testFile))


class CompareVersionTestCase(unittest.TestCase):
    def testComparingVersionsOfSameSize(self):
        self.assertTrue(compareVersions('1.0', '<', '2.0'))

    def testComparingWithoutGivingOperatorDefaultsToEqual(self):
        self.assertTrue(compareVersions('1.0', '', '1.0'))
        self.assertFalse(compareVersions('1', '', '2'))

    def testComparingWithOneEqualitySignWork(self):
        self.assertTrue(compareVersions('1.0', '=', '1.0'))

    def testUsingUnknownOperatorFails(self):
        self.assertRaises(Exception, compareVersions, '1', 'asdf', '2')
        self.assertRaises(Exception, compareVersions, '1', '+-', '2')
        self.assertRaises(Exception, compareVersions, '1', '<>', '2')
        self.assertRaises(Exception, compareVersions, '1', '!=', '2')

    def testIgnoringVersionsWithWaveInThem(self):
        self.assertTrue(compareVersions('1.0~20131212', '<', '2.0~20120101'))
        self.assertTrue(compareVersions('1.0~20131212', '==', '1.0~20120101'))

    def testUsingInvalidVersionStringsFails(self):
        self.assertRaises(Exception, compareVersions, 'abc-1.2.3-4', '==', '1.2.3-4')
        self.assertRaises(Exception, compareVersions, '1.2.3-4', '==', 'abc-1.2.3-4')

    def testComparingWorksWithLettersInVersionString(self):
        self.assertTrue(compareVersions('1.0.a', '<', '1.0.b'))
        self.assertTrue(compareVersions('a.b', '>', 'a.a'))

    def testComparisonsWithDifferntDepthsAreMadeTheSameDepth(self):
        self.assertTrue(compareVersions('1.1.0.1', '>', '1.1'))
        self.assertTrue(compareVersions('1.1', '<', '1.1.0.1'))

    def testPackageVersionsAreComparedAswell(self):
        self.assertTrue(compareVersions('1-2', '<', '1-3'))
        self.assertTrue(compareVersions('1-2.0', '<', '1-2.1'))


class GetGlobalConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.testFile = os.path.join(
            os.path.dirname(__file__), 'testdata', 'util', 'fake_global.conf'
        )

    def tearDown(self):
        del self.testFile

    def testCommentsAreIgnored(self):
        self.assertEqual("no", getGlobalConfig('comment', self.testFile))

    def testLinesNeedAssignments(self):
        self.assertEqual(None, getGlobalConfig('this', self.testFile))

    def testReadingValues(self):
        self.assertEqual("value", getGlobalConfig('keyword', self.testFile))
        self.assertEqual(
            "this works too",
            getGlobalConfig('value with spaces', self.testFile)
        )
        self.assertEqual(
            "we even can include a = and it works",
            getGlobalConfig('advanced value', self.testFile)
        )

    def testFileNotFoundExitsGracefully(self):
        self.assertEqual(None, getGlobalConfig('dontCare', 'nonexistingFile'))


class IsRegularExpressionTestCase(unittest.TestCase):
    def testIfIsRegExObject(self):
        self.assertFalse(isRegularExpressionPattern("no pattern"))
        self.assertFalse(isRegularExpressionPattern("SRE_Pattern"))

        self.assertTrue(isRegularExpressionPattern(re.compile("ABC")))


if __name__ == '__main__':
    unittest.main()
