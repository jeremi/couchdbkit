# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import os
import shutil
import tempfile
import unittest

from restkit import ResourceNotFound, RequestFailed

from couchdbkit import *
from couchdbkit.utils import *


class LoaderTestCase(unittest.TestCase):
    
    def setUp(self):
        f, fname = tempfile.mkstemp()
        os.unlink(fname)
        self.tempdir = fname
        os.makedirs(self.tempdir)
        
        self.template_dir = os.path.join(os.path.dirname(__file__), 'data/app-template')
        self.app_dir = os.path.join(self.tempdir, "couchdbkit-test")
        shutil.copytree(self.template_dir, self.app_dir)
        self.server = Server()
        self.db = self.server.create_db('couchdbkit_test')
        
    def tearDown(self):
        for root, dirs, files in os.walk(self.tempdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        del self.server['couchdbkit_test']
                
    def testGetDoc(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_(isinstance(design_doc, dict))
        self.assert_('_id' in design_doc)
        self.assert_(design_doc['_id'] == "_design/couchdbkit-test")
        self.assert_('lib' in design_doc)
        self.assert_('helpers' in design_doc['lib'])
        self.assert_('template' in design_doc['lib']['helpers'])
        
    def testGetDocView(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('views' in design_doc)
        self.assert_('example' in design_doc['views'])
        self.assert_('map' in design_doc['views']['example'])
        self.assert_('emit' in design_doc['views']['example']['map'])
        
    def testGetDocCouchApp(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('couchapp' in design_doc)
        
    def testGetDocManifest(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('manifest' in design_doc['couchapp'])
        self.assert_('lib/helpers/template.js' in design_doc['couchapp']['manifest'])
        self.assert_('foo/' in design_doc['couchapp']['manifest'])
        self.assert_(len(design_doc['couchapp']['manifest']) == 16)
        
        
    def testGetDocAttachments(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('_attachments' in design_doc)
        self.assert_('index.html' in design_doc['_attachments'])
        self.assert_('style/main.css' in design_doc['_attachments'])
        
        content = open(design_doc['_attachments']['style/main.css'], 'rb').read()
        self.assert_(content == "/* add styles here */")
        
    def testGetDocSignatures(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('signatures' in design_doc['couchapp'])
        self.assert_(len(design_doc['couchapp']['signatures']) == 2)
        self.assert_('index.html' in design_doc['couchapp']['signatures'])
        signature =  design_doc['couchapp']['signatures']['index.html']
        fsignature = sign_file(os.path.join(self.app_dir, '_attachments/index.html'))
        self.assert_(signature==fsignature)
        
    def _sync(self, atomic=True):
        l = FileSystemDocsLoader(self.tempdir)
        l.sync(self.db, atomic=atomic, verbose=True)
        # any design doc created ?
        design_doc = None
        try:
            design_doc = self.db['_design/couchdbkit-test']
        except ResourceNotFound:
            pass
        self.assert_(design_doc is not None)
        

        # should create view
        self.assert_('function' in design_doc['views']['example']['map'])
        
        # should use macros
        self.assert_('stddev' in design_doc['views']['example']['map'])
        self.assert_('ejohn.org' in design_doc['shows']['example-show'])
        
        # should have attachments
        self.assert_('_attachments' in design_doc)
        
        # should create index
        self.assert_(design_doc['_attachments']['index.html']['content_type'] == 'text/html')
        
        # should create manifest
        self.assert_('foo/' in design_doc['couchapp']['manifest'])
        
        # should push and macro the doc shows
        self.assert_('Generated CouchApp Form Template' in design_doc['shows']['example-show'])
        
        # should push and macro the view lists
        self.assert_('Test XML Feed' in design_doc['lists']['feed'])
        
        # should allow deeper includes
        self.assertFalse('"helpers"' in design_doc['shows']['example-show'])
        
        # deep require macros
        self.assertFalse('"template"' in design_doc['shows']['example-show'])
        self.assert_('Resig' in design_doc['shows']['example-show'])
        
    def testSync(self):
        self._sync()
        
    def testSyncNonAtomic(self):
        self._sync(atomic=False)
        
if __name__ == '__main__':
    unittest.main()
        
        


