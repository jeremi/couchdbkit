# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
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

import unittest

from restclient import ResourceNotFound, RequestFailed

from couchdbkit.resource import CouchdbResource
from couchdbkit.client import Server, Database, View

class ClientServerTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()
        
    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass

    def testGetInfo(self):
        info = self.Server.info()
        self.assert_(info.has_key('version'))
        
    def testCreateDb(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_(isinstance(res, Database) == True)
        all_dbs = self.Server.all_dbs()
        self.assert_('couchdbkit_test' in all_dbs)
        del self.Server['couchdbkit_test']

    def testGetOrCreateDb(self):
        # create the database
        self.assertFalse("get_or_create_db" in self.Server)
        gocdb = self.Server.get_or_create_db("get_or_create_db")
        self.assert_(gocdb.dbname == "get_or_create_db")
        self.assert_("get_or_create_db" in self.Server)
        self.Server.delete_db("get_or_create_db")
        # get the database (already created)
        self.assertFalse("get_or_create_db" in self.Server)
        db = self.Server.create_db("get_or_create_db")
        self.assert_("get_or_create_db" in self.Server)
        gocdb = self.Server.get_or_create_db("get_or_create_db")
        self.assert_(db.dbname == gocdb.dbname)
        self.Server.delete_db("get_or_create_db")
        
    def testBadResourceClassType(self):
        self.assertRaises(TypeError, Server, resource_class=None)
        
    def testServerLen(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_(len(self.Server) >= 1)
        self.assert_(bool(self.Server))
        del self.Server['couchdbkit_test']
        
    def testServerContain(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_('couchdbkit_test' in self.Server)
        del self.Server['couchdbkit_test']
        
        
    def testGetUUIDS(self):
        uuid = self.Server.next_uuid()
        self.assert_(isinstance(uuid, basestring) == True)
        self.assert_(len(self.Server.uuids) == 999)
        uuid2 = self.Server.next_uuid()
        self.assert_(uuid != uuid2)
        self.assert_(len(self.Server.uuids) == 998)
        
class ClientDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass
        
    def testCreateDatabase(self):
        db = self.Server.create_db('couchdbkit_test')
        self.assert_(isinstance(db, Database) == True)
        info = db.info()
        self.assert_(info['db_name'] == 'couchdbkit_test')
        del self.Server['couchdbkit_test']
        
    def testDbFromUri(self):
        db = self.Server.create_db('couchdbkit_test')
        
        db1 = Database.from_uri("http://127.0.0.1:5984/couchdbkit_test", "couchdbkit_test")
        self.assert_(hasattr(db1, "dbname") == True)
        self.assert_(db1.dbname == "couchdbkit_test")
        info = db1.info()
        self.assert_(info['db_name'] == "couchdbkit_test")
        

    def testCreateEmptyDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        del self.Server['couchdbkit_test']
        self.assert_('_id' in doc)
        
        
    def testCreateDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        # create doc without id
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        self.assert_(db.doc_exist(doc['_id']))
        # create doc with id
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        self.assert_(db.doc_exist('test'))
        doc2 = { 'string': 'test', 'number': 4 }
        db['test2'] = doc2
        self.assert_(db.doc_exist('test2'))
        del self.Server['couchdbkit_test']

            
    def testUpdateDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        doc.update({'number': 6})
        db.save_doc(doc)
        doc = db.get(doc['_id'])
        self.assert_(doc['number'] == 6)
        del self.Server['couchdbkit_test']
        
    def testDocWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': "a/b"}
        db.save_doc(doc)
        self.assert_( "a/b" in db) 
 
        doc = { '_id': "http://a"}
        db.save_doc(doc)
        self.assert_( "http://a" in db)
        doc = db.get("http://a")
        self.assert_(doc is not None)
 
        def not_found():
            doc = db.get('http:%2F%2Fa')
        self.assertRaises(ResourceNotFound, not_found)
 
        self.assert_(doc.get('_id') == "http://a")
        doc.get('_id')

        doc = { '_id': "http://b"}
        db.save_doc(doc)
        self.assert_( "http://b" in db)
 
        doc = { '_id': '_design/a' }
        db.save_doc(doc)
        self.assert_( "_design/a" in db)
        del self.Server['couchdbkit_test']
    
    def testMultipleDocWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': "a/b"}
        doc1 = { '_id': "http://a"}
        doc3 = { '_id': '_design/a' }
        db.bulk_save([doc, doc1, doc3])
        self.assert_( "a/b" in db) 
        self.assert_( "http://a" in db)
        self.assert_( "_design/a" in db)
        def not_found():
            doc = db.get('http:%2F%2Fa')
        self.assertRaises(ResourceNotFound, not_found)
        del self.Server['couchdbkit_test']
    
    def testDbLen(self):
        db = self.Server.create_db('couchdbkit_test')
        doc1 = { 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        doc2 = { 'string': 'test2', 'number': 4 }
        db.save_doc(doc2)

        self.assert_(len(db) == 2)
        del self.Server['couchdbkit_test']
        
    def testDeleteDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        docid=doc['_id']
        db.delete_doc(docid)
        self.assert_(db.doc_exist(docid) == False)
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        docid=doc['_id']
        db.delete_doc(doc)
        self.assert_(db.doc_exist(docid) == False)
        del self.Server['couchdbkit_test']

    def testStatus404(self):
        db = self.Server.create_db('couchdbkit_test')

        def no_doc():
            doc = db.get('t')

        self.assertRaises(ResourceNotFound, no_doc)
        
        del self.Server['couchdbkit_test']
        
    def testInlineAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        doc = { 
            '_id': "docwithattachment", 
            "f": "value", 
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                }
            }
        }
        db.save_doc(doc)
        fetch_attachment = db.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        doc1 = db.get("docwithattachment")
        self.assert_('_attachments' in doc1)
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('stub' in doc1['_attachments']['test.html'])
        self.assert_(doc1['_attachments']['test.html']['stub'] == True)
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        del self.Server['couchdbkit_test']
    
    def testMultipleInlineAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        attachment2 = "<html><head><title>test attachment</title></head><body><p>More words</p></body></html>"
        doc = { 
            '_id': "docwithattachment", 
            "f": "value", 
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                },
                "test2.html": {
                    "type": "text/html",
                    "data": attachment2
                }
            }
        }
        
        db.save_doc(doc)
        fetch_attachment = db.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        fetch_attachment = db.fetch_attachment(doc, "test2.html")
        self.assert_(attachment2 == fetch_attachment)
        
        doc1 = db.get("docwithattachment")
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('test2.html' in doc1['_attachments'])
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc1['_attachments']['test2.html']['length'])
        del self.Server['couchdbkit_test']
        
    def testInlineAttachmentWithStub(self):
        db = self.Server.create_db('couchdbkit_test')
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        attachment2 = "<html><head><title>test attachment</title></head><body><p>More words</p></body></html>"
        doc = { 
            '_id': "docwithattachment", 
            "f": "value", 
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                }
            }
        }
        db.save_doc(doc)
        doc1 = db.get("docwithattachment")
        doc1["_attachments"].update({
            "test2.html": {
                "type": "text/html",
                "data": attachment2
            }
        })
        db.save_doc(doc1)
        
        fetch_attachment = db.fetch_attachment(doc1, "test2.html")
        self.assert_(attachment2 == fetch_attachment)
        
        doc2 = db.get("docwithattachment")
        self.assert_('test.html' in doc2['_attachments'])
        self.assert_('test2.html' in doc2['_attachments'])
        self.assert_(len(attachment) == doc2['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc2['_attachments']['test2.html']['length'])
        del self.Server['couchdbkit_test']
        
    def testAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']
   
    def testEmptyAttachment(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        db.put_attachment(doc, "", name="test")
        doc1 = db.get(doc['_id'])
        attachment = doc1['_attachments']['test']
        self.assertEqual(0, attachment['length'])
        del self.Server['couchdbkit_test']

    def testDeleteAttachment(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        
        text_attachment = "un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        db.delete_attachment(doc, 'test')
        attachment = db.fetch_attachment(doc, 'test')
        self.assert_(attachment == None)
        del self.Server['couchdbkit_test']
        
    def testAttachmentsWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': 'test/slashes', 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        
        db.put_attachment(doc, text_attachment, "test/test.txt", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test/test.txt")
        self.assert_(text_attachment == fetch_attachment)
        
        del self.Server['couchdbkit_test']
        
        
    def testAttachmentUnicode8URI(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': u"éàù/slashes", 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']
        
    def testSaveMultipleDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        self.assert_('_id' in docs[0])
        self.assert_('_rev' in docs[0])
        doc = db.get(docs[2]['_id'])
        self.assert_(doc['number'] == 4)
        docs[3]['number'] = 6
        old_rev = docs[3]['_rev']
        db.bulk_save(docs)
        self.assert_(docs[3]['_rev'] != old_rev)
        doc = db.get(docs[3]['_id'])
        self.assert_(doc['number'] == 6)
        docs = [
                { '_id': 'test', 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { '_id': 'test2', 'string': 'test', 'number': 42 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        doc = db.get('test2')
        self.assert_(doc['number'] == 42) 
        del self.Server['couchdbkit_test']
   
    def testDeleteMultipleDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        db.bulk_delete(docs)
        self.assert_(len(db) == 0)
        self.assert_(db.info()['doc_del_count'] == 4)

        del self.Server['couchdbkit_test']
        
    def testCopy(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { "f": "a" }
        db.save_doc(doc)
        
        db.copy_doc(doc['_id'], "test")
        self.assert_("test" in db)
        doc1 = db.get("test")
        self.assert_('f' in doc1)
        self.assert_(doc1['f'] == "a")
        
        db.copy_doc(doc, "test2")
        self.assert_("test2" in db)
        
        doc2 = { "_id": "test3", "f": "c"}
        db.save_doc(doc2)
        
        db.copy_doc(doc, doc2)
        self.assert_("test3" in db)
        doc3 = db.get("test3")
        self.assert_(doc3['f'] == "a")
        
        doc4 = { "_id": "test5", "f": "c"}
        db.save_doc(doc4)
        db.copy_doc(doc, "test6")
        doc6 = db.get("test6")
        self.assert_(doc6['f'] == "a")
        
        del self.Server['couchdbkit_test']


class ClientViewTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass

        try:
            self.Server.delete_db('couchdbkit_test2')
        except:
            pass

    def testView(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
                }
            }
        }
        db.save_doc(design_doc)
        
        doc3 = db.get('_design/test')
        self.assert_(doc3 is not None) 
        results = db.view('test/all')
        self.assert_(len(results) == 2)
        del self.Server['couchdbkit_test']

    def testAllDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)
        
        self.assert_(db.view('_all_docs').count() == 2 )
        self.assert_(db.view('_all_docs').all() == db.all_docs().all())

        del self.Server['couchdbkit_test']

    def testAllDocsBySeq(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)
        
        self.assert_(db.view('_all_docs_by_seq').count() == 2 )
        self.assert_(db.view('_all_docs_by_seq').all() == db.all_docs(by_seq=True).all())
        results = db.all_docs(by_seq=True).all()
        self.assert_(sorted([i["id"] for i in results]) == ["test", "test2"])
        self.assert_(sorted([i["key"] for i in results]) == [1,2])

        del self.Server['couchdbkit_test']




    def testCount(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc); }}"""
                }
            }
        }
        db.save_doc(design_doc)
        count = db.view('/test/all').count()
        self.assert_(count == 2)
        del self.Server['couchdbkit_test']

    def testTemporaryView(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
        }
         
        results = db.temp_view(design_doc)
        self.assert_(len(results) == 2)
        del self.Server['couchdbkit_test']


    def testView2(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test1', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)
        doc3 = { '_id': 'test3', 'string': 'test', 'number': 2,
                    'docType': 'test2'}
        db.save_doc(doc3)
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'with_test': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
                },
                'with_test2': {
                    "map": """function(doc) { if (doc.docType == "test2") { emit(doc._id, doc);
}}"""
                }   

            }
        }
        db.save_doc(design_doc)

        # yo view is callable !
        results = db.view('test/with_test')
        self.assert_(len(results) == 2)
        results = db.view('test/with_test2')
        self.assert_(len(results) == 1)
        del self.Server['couchdbkit_test']

    def testViewWithParams(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test1', 'string': 'test', 'number': 4, 
                'docType': 'test', 'date': '20081107' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                'docType': 'test', 'date': '20081107'}
        db.save_doc(doc2)
        doc3 = { '_id': 'test3', 'string': 'machin', 'number': 2,
                    'docType': 'test', 'date': '20081007'}
        db.save_doc(doc3)
        doc4 = { '_id': 'test4', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081108'}
        db.save_doc(doc4)
        doc5 = { '_id': 'test5', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081109'}
        db.save_doc(doc5)
        doc6 = { '_id': 'test6', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081109'}
        db.save_doc(doc6)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'test1': {
                    "map": """function(doc) { if (doc.docType == "test")
                    { emit(doc.string, doc);
}}"""
                },
                'test2': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc.date, doc);
}}"""
                },
                'test3': {
                    "map": """function(doc) { if (doc.docType == "test")
                    { emit(doc.string, doc);
}}"""
                }


            }
        }
        db.save_doc(design_doc)

        results = db.view('test/test1')
        self.assert_(len(results) == 6)

        results = db.view('test/test3', key="test")
        self.assert_(len(results) == 2)

       

        results = db.view('test/test3', key="test2")
        self.assert_(len(results) == 3)

        results = db.view('test/test2', startkey="200811")
        self.assert_(len(results) == 5)

        results = db.view('test/test2', startkey="20081107",
                endkey="20081108")
        self.assert_(len(results) == 3)

        results = db.view('test/test1', keys=['test', 'machin'] )
        self.assert_(len(results) == 3)

        del self.Server['couchdbkit_test']

        

if __name__ == '__main__':
    unittest.main()

