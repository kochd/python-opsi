# -*- coding: utf-8 -*-
"""
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope thatf it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright: uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

import testtools
from testtools.matchers import Annotate, Not

from OPSI.tests.helper.matchers import In, GreaterThan


class TestCase(testtools.TestCase):
	
	def setUp(self):
		super(TestCase, self).setUp()
		
		from OPSI.Logger import Logger
		logger = Logger()
		logger.setConsoleLevel(0)
		logger.setFileLevel(0)
		
	def useFixture(self, fixture):
		fixture.test = self
		return super(TestCase, self).useFixture(fixture)

	def assertIn(self, needle, haystack, message=''):
		matcher = In(haystack)
		if message:
			matcher = Annotate(message, matcher)
		self.assertThat(needle, matcher)
		
	def assertNotIn(self, needle, haystack, message=''):
		matcher = Not(In(haystack))
		if message:
			matcher = Annotate(message, matcher)
		self.assertThat(needle, matcher)

	def assertGreater(self, matchee, expected, message=''):
		matcher = GreaterThan(expected)
		if message:
			matcher = Annotate(message, matcher)
		self.assertThat(matchee, matcher)