# -*- test-case-name: OPSI.web2.dav.test.test_delete -*-
##
# Copyright (c) 2005 Apple Computer, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# DRI: Wilfredo Sanchez, wsanchez@apple.com
##

"""
WebDAV DELETE method
"""

__all__ = ["http_DELETE"]

from twisted.python import log
from twisted.internet.defer import waitForDeferred, deferredGenerator
from OPSI.web2 import responsecode
from OPSI.web2.http import HTTPError
from OPSI.web2.dav import davxml
from OPSI.web2.dav.fileop import delete
from OPSI.web2.dav.util import parentForURL

def http_DELETE(self, request):
    """
    Respond to a DELETE request. (RFC 2518, section 8.6)
    """
    if not self.fp.exists():
        log.err("File not found: %s" % (self.fp.path,))
        raise HTTPError(responsecode.NOT_FOUND)

    depth = request.headers.getHeader("depth", "infinity")

    #
    # Check authentication and access controls
    #
    parent = waitForDeferred(request.locateResource(parentForURL(request.uri)))
    yield parent
    parent = parent.getResult()

    x = waitForDeferred(parent.authorize(request, (davxml.Unbind(),)))
    yield x
    x.getResult()

    # Do quota checks before we start deleting things
    myquota = waitForDeferred(self.quota(request))
    yield myquota
    myquota = myquota.getResult()
    if myquota is not None:
        old_size = waitForDeferred(self.quotaSize(request))
        yield old_size
        old_size = old_size.getResult()
    else:
        old_size = 0

    # Do delete
    x = waitForDeferred(delete(request.uri, self.fp, depth))
    yield x
    result = x.getResult()

    # Adjust quota
    if myquota is not None:
        d = waitForDeferred(self.quotaSizeAdjust(request, -old_size))
        yield d
        d.getResult()
    
    yield result

http_DELETE = deferredGenerator(http_DELETE)
