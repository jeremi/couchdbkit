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

import datetime
import decimal
import unittest

from couchdbkit import *

class DocumentTestCase(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        try:
            self.server.delete_db('couchdbkit_test')
        except:
            pass

        try:
            self.server.delete_db('couchdbkit_test2')
        except:
            pass

    def testStaticDocumentCreation(self):
        db = self.server.create_db('couchdbkit_test')

        # with _allow_dynamic_properties
        class Test(Document):
            _allow_dynamic_properties = False
            foo = StringProperty()
        Test._db = db

        doc = Test()
        doc.foo="test"
        try:
            doc.bar="bla"
        except AttributeError, e:
            self.assert_(str(e) == "bar is not defined in schema (not a valid property)")
        doc.save()
        self.assert_(not hasattr(doc, "bar"))
        assert doc._doc['foo'] == "test"

        # With StaticDocument
        class Test(StaticDocument):
            foo = StringProperty()
        Test._db = db

        doc = Test()
        doc.foo="test"
        try:
            doc.bar="bla"
        except AttributeError, e:
            self.assert_(str(e) == "bar is not defined in schema (not a valid property)")
        doc.save()
        self.assert_(not hasattr(doc, "bar"))
        self.assert_(doc._doc['foo'] == "test")

        self.server.delete_db('couchdbkit_test')


    def testDynamicDocumentCreation(self):
        class Test(Document):
            pass

        class Test2(Document):
            string = StringProperty(default="test")


        doc = Test(string="essai")
        self.assert_(getattr(doc, 'string') is not None)
        self.assert_(doc.string == "essai")

        doc1 = Test(string="essai", string2="essai2")
        self.assert_(doc1.string == "essai")
        self.assert_(doc1.string2 == "essai2")

        doc2 = Test2(string2="essai")
        self.assert_(doc2.string == "test")

    def testDeleteProperty(self):
        class Test(Document):
            string = StringProperty(default="test")

        doc = Test(string="test")
        del doc.string
        self.assert_(getattr(doc, "string") == None)
        self.assert_(doc['string'] == None)

        class Test2(Document):
            pass

        doc1 = Test2(string="test")
        del doc1.string
        self.assert_(getattr(doc, "string") == None)
 

    def testContain(self):
        class Test(Document):
            string = StringProperty(default="test")
        doc = Test()
        self.assert_('string' in doc)
        self.assert_('test' not in doc)

        doc.test = "test"
        self.assert_('test' in doc)

    def testLen(self):
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()

        doc = Test()
        self.assert_(len(doc) == 3)
        doc.string3 = "4"
        self.assert_(len(doc) == 4) 
        
    def testStore(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()
        Test._db = db

        doc = Test()
        doc.string2 = "test2"

        doc.save()
        self.assert_(doc._id is not None)
        doc1 = db.get(doc._id)
        self.assert_(doc1['string2'] == "test2")

        doc2 = Test(string3="test")
        doc2.save()
        doc3 = db.get(doc2._id)
        self.assert_(doc3['string3'] == "test")

        self.server.delete_db('couchdbkit_test')

    def testBulkSave(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty()
        #Test._db = db
        class Test2(Document):
            string = StringProperty()

        doc1 = Test(string="test")
        self.assert_(doc1._id is None)
        doc2 = Test(string="test2")
        self.assert_(doc2._id is None)
        doc3 = Test(string="test3")
        self.assert_(doc3._id is None)

        try:
            Test.bulk_save( [doc1, doc2, doc3] )
        except TypeError, e:
            self.assert_(str(e)== "doc database required to save document" )

        Test.set_db( db )
        bad_doc = Test2(string="bad_doc")
        try:
            Test.bulk_save( [doc1, doc2, doc3, bad_doc] )
        except ValueError, e:
            self.assert_(str(e) == "one of your documents does not have the correct type" )

        Test.bulk_save( [doc1, doc2, doc3] )
        self.assert_(doc1._id is not None)
        self.assert_(doc1._rev is not None)
        self.assert_(doc2._id is not None)
        self.assert_(doc2._rev is not None)
        self.assert_(doc3._id is not None)
        self.assert_(doc3._rev is not None)
        self.assert_(doc1.string == "test")
        self.assert_(doc2.string == "test2")
        self.assert_(doc3.string == "test3")

        self.server.delete_db('couchdbkit_test')

 

    def testGet(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()
        Test._db = db

        doc = Test()
        doc.string2 = "test2"
        doc.save()
        doc2 = Test.get(doc._id)

        self.assert_(doc2.string2 == "test2")
    
        doc2.string3 = "blah"
        doc2.save()
        doc3 = db.get(doc2._id)
        self.assert_(doc3)

        self.server.delete_db('couchdbkit_test')

    def testLoadDynamicProperties(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            pass
        Test._db = db

        doc = Test(field="test",
                field1=datetime.datetime(2008, 11, 10, 8, 0, 0),
                field2=datetime.date(2008, 11, 10),
                field3=datetime.time(8, 0, 0),
                field4=decimal.Decimal("45.4"),
                field5=4.4)
        doc.save()
        doc1 = Test.get(doc._id)
        self.server.delete_db('couchdbkit_test')

        self.assert_(isinstance(doc1.field, basestring))
        self.assert_(isinstance(doc1.field1, datetime.datetime))
        self.assert_(isinstance(doc1.field2, datetime.date))
        self.assert_(isinstance(doc1.field3, datetime.time))
        self.assert_(isinstance(doc1.field4, decimal.Decimal))
        self.assert_(isinstance(doc1.field5, float))

    def testDocType(self):
        class Test(Document):
            string = StringProperty(default="test")
        
        class Test2(Document):
            string = StringProperty(default="test")
            
        class Test3(Document):
            doc_type = "test_type"
            string = StringProperty(default="test")

        doc1 = Test() 
        doc2 = Test2()
        doc3 = Test2()
        doc4 = Test3()

        self.assert_(doc1._doc_type == 'Test')
        self.assert_(doc1._doc['doc_type'] == 'Test')
        
        self.assert_(doc3._doc_type == 'Test2')
        self.assert_(doc4._doc_type == 'test_type')
        self.assert_(doc4._doc['doc_type'] == 'test_type')
        
        
        db = self.server.create_db('couchdbkit_test')
        Test3._db = Test2._db = Test._db = db

        doc1.save()
        doc2.save()
        doc3.save()
        doc4.save()
     
        get1 = Test.get(doc1._id)
        get2 = Test2.get(doc2._id)
        get3 = Test2.get(doc3._id)
        get4 = Test3.get(doc4._id)


        self.server.delete_db('couchdbkit_test')
        self.assert_(get1._doc['doc_type'] == 'Test')
        self.assert_(get2._doc['doc_type']== 'Test2')
        self.assert_(get3._doc['doc_type'] == 'Test2')
        self.assert_(get4._doc['doc_type'] == 'test_type')
        
    def testInheriting(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        class TestDoc2(TestDoc):
            field3 = StringProperty()
           
        doc = TestDoc2(field1="a", field2="b",
                field3="c")
        doc2 = TestDoc2(field1="a", field2="b",
                field3="c", field4="d")

        self.assert_(len(doc2._dynamic_properties) == 1)

    def testView(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        doc3 = list(results)[0]
        self.assert_(hasattr(doc3, "field1"))
        self.server.delete_db('couchdbkit_test')
    
    def testViewNoneValue(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, null);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db
        
        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        self.assert_(isinstance(results.first(), dict) == True)
        results2 = TestDoc.view('test/all', include_docs=True)
        self.assert_(len(results2) == 2)
        self.assert_(isinstance(results2.first(), TestDoc) == True)       
        self.server.delete_db('couchdbkit_test')
        
        
    def testOne(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

       
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 0)
        self.assertRaises(NoResultFound, results.one, except_all=True)
        rst = results.one()
        self.assert_(rst is None)
        
        
        results = TestDoc.view('test/all')
        doc.save()
        self.assert_(len(results) == 1)
        
        one = results.one()
        self.assert_(isinstance(one, TestDoc) == True)
        
        doc1.save()
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        
        self.assertRaises(MultipleResultsFound, results.one)

        self.server.delete_db('couchdbkit_test')
        
    def testViewStringValue(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()
        
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc.field1);}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")
        
        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        self.server.delete_db('couchdbkit_test')
        

    def testTempView(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()
        
        design_doc = {
            "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
        }
       
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db
        
        doc.save()
        doc1.save()
        results = TestDoc.temp_view(design_doc)
        self.assert_(len(results) == 2)
        doc3 = list(results)[0]
        self.assert_(hasattr(doc3, "field1"))
        self.server.delete_db('couchdbkit_test')
    
    def testDocumentAttachments(self):
        db = self.server.create_db('couchdbkit_test')
        
        class A(Document):
            s = StringProperty(default='test')
            i = IntegerProperty(default=4)
        A._db = db

        a = A()
        a.save()
  
        text_attachment = u"un texte attaché"
        old_rev = a._rev

        a.put_attachment(text_attachment, "test", "text/plain")
        self.assert_(old_rev != a._rev)
        fetch_attachment = a.fetch_attachment("test")
        self.assert_(text_attachment == fetch_attachment)
        self.server.delete_db('couchdbkit_test')
   

    def testDocumentDeleteAttachment(self):
        db = self.server.create_db('couchdbkit_test')
        class A(Document):
            s = StringProperty(default='test')
            i = IntegerProperty(default=4)
        A._db = db

        a = A()
        a.save()
        
        text_attachment = "un texte attaché"
        old_rev = a._rev
        
        a.put_attachment(text_attachment, "test", "text/plain")
        a.delete_attachment('test')
        attachment = a.fetch_attachment('test')
        self.assert_(attachment == None)
        
        self.server.delete_db('couchdbkit_test')

    def testScopedSession(self):
        db = self.server.create_db('couchdbkit_test')
        dbsession = create_session(self.server,
                'couchdbkit_test')

        class A(Document):
            s = StringProperty()

        a = A()
        a.s = "test"
        dbsession(a).save()
        
        b = dbsession(A).get(a._id)

        self.assert_(b.s == "test")
        
        c = A.get(a._id)
        self.assert_(c.s == "test")
        
        self.server.delete_db('couchdbkit_test')

    def testSccopedSesion2(self):
        db = self.server.create_db('couchdbkit_test')
        db2 = self.server.create_db('couchdbkit_test2')

        session = dbsession = create_session(self.server,
                'couchdbkit_test')

        session2 = dbsession = create_session(self.server,
                'couchdbkit_test')

        class A(Document):
            s = StringProperty()

        a = A()
        a.s = "test"
        session(a).save()

        a2 = A()
        a2.s = "test2"
        session2(a2).save()

        b = session(A).get(a._id)
        self.assert_(b.s == "test")

        b2 = session2(A).get(a2._id)
        self.assert_(b2.s == "test2")

        self.server.delete_db('couchdbkit_test')
        self.server.delete_db('couchdbkit_test2')

    def testGetOrCreate(self):
        self.server.create_db('couchdbkit_test')
        db = create_session(self.server, 'couchdbkit_test')

        class A(Document):
            s = StringProperty()
        A = db(A)

        def no_exist():
            a = A.get('test')

        self.assertRaises(ResourceNotFound, no_exist)

        a = A.get_or_create('test')
        self.assert_(a.id == "test")
        
        b = A.get_or_create()
        self.assert_(a.id is not None)
        self.server.delete_db('couchdbkit_test')


class PropertyTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        try:
            self.db = self.server.create_db('couchdbkit_test')
        except: 
            # waiting we fix all tests use created db
            self.db = self.server['couchdbkit_test']
            
    def tearDown(self):
        try:
            self.server.delete_db('couchdbkit_test')
        except:
            pass

    def testRequired(self):
        class Test(Document):
            string = StringProperty(required=True)
        Test._db = self.db

        test = Test()
        def ftest():
            test.string = ""
        self.assertRaises(BadValueError, test.save)

    def testValidator(self):
        def test_validator(value):
            if value == "test":
                raise BadValueError("test")

        class Test(Document):
            string = StringProperty(validators=test_validator)

        test = Test()
        def ftest():
            test.string = "test"
        self.assertRaises(BadValueError, ftest)

    def testIntegerProperty(self):
        class Test(Document):
            field = IntegerProperty()
        
        test = Test()
        def ftest():
            test.field = "essai" 
        
        
        self.assertRaises(BadValueError, ftest)
        test.field = 4
        self.assert_(test._doc['field'] == 4)

    def testDateTimeProperty(self):
        class Test(Document):
            field = DateTimeProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.datetime(2008, 11, 10, 8, 0, 0)
        self.assert_(test._doc['field'] == "2008-11-10T08:00:00Z")
        value = test.field
        self.assert_(isinstance(value, datetime.datetime))
        
    def testDateProperty(self):
        class Test(Document):
            field = DateProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.date(2008, 11, 10)
        self.assert_(test._doc['field'] == "2008-11-10")
        value = test.field
        self.assert_(isinstance(value, datetime.date))


    def testTimeProperty(self):
        class Test(Document):
            field = TimeProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.time(8, 0, 0)
        self.assert_(test._doc['field'] == "08:00:00")
        value = test.field
        self.assert_(isinstance(value, datetime.time))

    def testMixProperties(self):
        class Test(Document):
            field = StringProperty()
            field1 = DateTimeProperty()

        test = Test(field="test", 
                field1 = datetime.datetime(2008, 11, 10, 8, 0, 0))

        self.assert_(test._doc['field'] == "test")
        self.assert_(test._doc['field1'] == "2008-11-10T08:00:00Z")
       
        self.assert_(isinstance(test.field, basestring))
        self.assert_(isinstance(test.field1, datetime.datetime))
        Test._db = self.db
        test.save()
        doc2 = Test.get(test._id)
        
        v = doc2.field
        v1 = doc2.field1
        self.assert_(isinstance(v, basestring))
        self.assert_(isinstance(v1, datetime.datetime))
    
    def testMixDynamicProperties(self):
        class Test(Document):
            field = StringProperty()
            field1 = DateTimeProperty()

        test = Test(field="test", 
                field1 = datetime.datetime(2008, 11, 10, 8, 0, 0),
                dynamic_field = 'test')

        Test._db = self.db

        test.save()

        doc2 = Test.get(test._id)

        v1 = doc2.field1
        vd = doc2.dynamic_field

        self.assert_(isinstance(v1, datetime.datetime))
        self.assert_(isinstance(vd, basestring))


    def testSchemaProperty1(self):
        class MySchema(DocumentSchema):
            astring = StringProperty()

        class MyDoc(Document):
            schema = SchemaProperty(MySchema)

        doc = MyDoc()
        self.assert_('schema' in doc._doc)
        
        doc.schema.astring = u"test"
        self.assert_(doc.schema.astring == u"test")
        self.assert_(doc._doc['schema']['astring'] == u"test")
        
        MyDoc._db = self.db

        doc.save()
        doc2 = MyDoc.get(doc._id)
        
        self.assert_(isinstance(doc2.schema, MySchema) == True)
        self.assert_(doc2.schema.astring == u"test")
        self.assert_(doc2._doc['schema']['astring'] == u"test")


    def testSchemaPropertyWithRequired(self):
        class B( Document ):
            class b_schema(DocumentSchema):
                name = StringProperty(  required = True, default = "name" )
            b = SchemaProperty( b_schema )
            
        B._db = self.db
        
        b = B()
        self.assertEquals(b.b.name, "name" )

        def bad_value():
            b.b.name = 4 
        self.assertRaises(BadValueError, bad_value)

        b1 = B()
        try:
            b1.b.name = 3
            raise RuntimeError
        except BadValueError:
            pass
        b1.b.name = u"test"


    def testSchemaWithPythonTypes(self):
        class A(Document):
            c = unicode()
            i = int(4)
        a = A()
        self.assert_(a._doc == {'c': u'', 'doc_type': 'A', 'i': 4})
        def bad_value():
            a.i = "essai"

        self.assertRaises(BadValueError, bad_value)

    def testSchemaBuild(self):
        schema = DocumentSchema(i = IntegerProperty())
        C = DocumentSchema.build(**schema._dynamic_properties)
        self.assert_('i' in C._properties)
        self.assert_(isinstance(C.i, IntegerProperty))

        c = C()
        self.assert_(c._doc_type == 'AnonymousSchema')
        self.assert_(c._doc == {'doc_type': 'AnonymousSchema', 'i':
            None})


        schema2 = DocumentSchema(i = IntegerProperty(default=-1))
        C3 = DocumentSchema.build(**schema2._dynamic_properties)
        c3 = C3()

        self.assert_(c3._doc == {'doc_type': 'AnonymousSchema', 'i':
            -1})
        self.assert_(c3.i == -1)

        def bad_value():
            c3.i = "test"

        self.assertRaises(BadValueError, bad_value)
        self.assert_(c3.i == -1)

    def testSchemaPropertyValidation2(self):
        class Foo( Document ):
            bar = SchemaProperty(DocumentSchema(foo=IntegerProperty()))

        doc = Foo()
        def bad_value():
            doc.bar.foo = "bla"
        self.assertRaises(BadValueError, bad_value)
    
   
    def testDynamicSchemaProperty(self):
        from datetime import datetime
        class A(DocumentSchema):
            s = StringProperty()
            
        a = A(s="foo")

        class B(Document):
            s1 = StringProperty()
            s2 = StringProperty()
            sm = SchemaProperty(a)
        
        b = B()
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': u'foo'}})

        b.created = datetime(2009, 2, 6, 18, 58, 20, 905556)
        self.assert_(b._doc == {'created': '2009-02-06T18:58:20Z',
            'doc_type': 'B',
            's1': None,
            's2': None,
            'sm': {'doc_type': 'A', 's': u'foo'}})

        self.assert_(isinstance(b.created, datetime) == True)

        a.created = datetime(2009, 2, 6, 20, 58, 20, 905556)
        self.assert_(a._doc ==  {'created': '2009-02-06T20:58:20Z',
            'doc_type': 'A', 's': u'foo'})

        self.assert_(b._doc == {'created': '2009-02-06T18:58:20Z',
            'doc_type': 'B',
            's1': None,
            's2': None,
            'sm': {'created': '2009-02-06T20:58:20Z', 'doc_type': 'A',
            's': u'foo'}})


        b2 = B()
        b.s1 = "t1"

        self.assert_(b2.sm._doc == b.sm._doc)
        self.assert_(b.s1 != b2.s1)

        b2.sm.s3 = "t2"
        self.assert_(b2.sm.s3 == b.sm.s3)
        self.assert_(b.s1 != b2.s1)

        b.sm.s3 = "t3"
        self.assert_(b2.sm.s3 == "t3")

    def testStaticSchemaProperty(self):
        from datetime import datetime
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            s1 = StringProperty()
            s2 = StringProperty()
            sm = SchemaProperty(A)
       
        b = B()
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': None}})

        b.sm.s = "t1"
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': u't1'}})

        b2 = B()
        self.assert_(b2._doc == {'doc_type': 'B', 's1': None, 's2':
            None, 'sm': {'doc_type': 'A', 's': None}})

        b2.sm.s = "t2"
        self.assert_(b2._doc == {'doc_type': 'B', 's1': None, 's2':
            None, 'sm': {'doc_type': 'A', 's': u't2'}})

        self.assert_(b2.sm.s != b.sm.s)

    def testListProperty(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(datetime)
        A.set_db(self.db) 
            
        # we can save an empty list
        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'l': []})
        a.save()
        self.assert_(a['_id'])
        self.assert_(a['l']==[])
        
        a = A()
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.l.append(d)
        self.assert_(len(a.l) == 1)
        self.assert_(a.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z']})
        a.l.append({ 's': "test"})
        self.assert_(a.l == [datetime(2009, 4, 13, 22, 56, 10), {'s': 'test'}])
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z', {'s': 'test'}]}
        )
        
        a.save()
        
        b = A.get(a._id)
        self.assert_(len(b.l) == 2)
        self.assert_(b.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(b._doc['l'] == ['2009-04-13T22:56:10Z', {'s': 'test'}])
        
        
        a = A(l=["a", "b", "c"])
        a.save()
        b = self.db.get(a._id, wrapper=A.wrap)
        self.assert_(a.l == ["a", "b", "c"])
        b.l = []
        self.assert_(b.l == [])
        self.assert_(b.to_json()['l'] == [])
        
       
        
    def testListPropertyNotEmpty(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(datetime, required=True)

        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'l': []})
        self.assertRaises(BadValueError, a.save)
        try:
            a.validate()
        except BadValueError, e:
            pass
        self.assert_(str(e) == 'Property l is required.')
        
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.l.append(d)
        self.assert_(len(a.l) == 1)
        self.assert_(a.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z']})
        a.validate()
        
        class A2(Document):
            l = ListProperty()
            
        a2 = A2()            
        self.assertTrue(a2.validate(required=False))
        self.assertTrue(a2.validate())
    
    def testListPropertyWithType(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)
        a = A()    
        a.l.append("test")
        self.assertRaises(BadValueError, a.validate)
        
        class B(Document):
            ls = StringListProperty()
        b = B()
        b.ls.append("test")
        self.assertTrue(b.validate())
        b.ls.append(datetime.utcnow())
        self.assertRaises(BadValueError, b.validate)
        
         
    def testDictProperty(self):
        from datetime import datetime
        class A(Document):
            d = DictProperty()
        A.set_db(self.db)
            
        a = A()
        self.assert_(a._doc == {'d': {}, 'doc_type': 'A'})
        a.d['s'] = 'test'
        self.assert_(a._doc == {'d': {'s': 'test'}, 'doc_type': 'A'})
        a.d['created'] = datetime(2009, 4, 16, 16, 5, 41)
        self.assert_(a._doc == {'d': {'created': '2009-04-16T16:05:41Z', 's': 'test'}, 'doc_type': 'A'})
        self.assert_(isinstance(a.d['created'], datetime) == True)
        a.d.update({'s2': 'test'})
        self.assert_(a.d['s2'] == 'test')
        a.d.update({'d2': datetime(2009, 4, 16, 16, 5, 41)})
        self.assert_(a._doc['d']['d2'] == '2009-04-16T16:05:41Z')
        self.assert_(a.d['d2'] == datetime(2009, 4, 16, 16, 5, 41))
        self.assert_(a.d == {'s2': 'test', 's': 'test', 'd2': datetime(2009, 4, 16, 16, 5, 41), 'created': datetime(2009, 4, 16, 16, 5, 41)})
        
        a = A()
        a.d['test'] = { 'a': datetime(2009, 5, 10, 21, 19, 21, 127380) }
        self.assert_(a.d == { 'test': {'a': datetime(2009, 5, 10, 21, 19, 21)}})
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z'}}, 'doc_type': 'A'} )
        
        a.d['test']['b'] = "essai"
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['essai'] = "test"
        self.assert_(a.d == {'essai': 'test',
         'test': {'a': datetime(2009, 5, 10, 21, 19, 21),
                  'b': 'essai'}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}},
         'doc_type': 'A'})
         
        del a.d['test']['a']
        self.assert_(a.d == {'essai': 'test', 'test': {'b': 'essai'}})
        self.assert_(a._doc ==  {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['test']['essai'] = { "a": datetime(2009, 5, 10, 21, 21, 11) }
        self.assert_(a.d == {'essai': 'test',
         'test': {'b': 'essai',
                  'essai': {'a': datetime(2009, 5, 10, 21, 21, 11)}}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test',
               'test': {'b': 'essai', 'essai': {'a': '2009-05-10T21:21:11Z'}}},
         'doc_type': 'A'}
        )
        
        del a.d['test']['essai']
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
        a = A()
        a.d['s'] = "level1"
        a.d['d'] = {}
        a.d['d']['s'] = "level2"
        self.assert_(a._doc == {'d': {'d': {'s': 'level2'}, 's': 'level1'}, 'doc_type': 'A'})
        a.save()
        a1 = A.get(a._id)
        a1.d['d']['s'] = "level2 edited"
        self.assert_(a1.d['d']['s'] == "level2 edited")
        self.assert_(a1._doc['d']['d']['s'] == "level2 edited")
        
    def testDictPropertyNotEmpty(self):
        from datetime import datetime
        class A(Document):
            d = DictProperty(required=True)
        A.set_db(self.db) 

        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'd': {}})
        self.assertRaises(BadValueError, a.save)
        try:
            a.save()
        except BadValueError, e:
            pass
        self.assert_(str(e) == 'Property d is required.')
        
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.d['date'] = d
        self.assert_(a.d['date'] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'd': { 'date': '2009-04-13T22:56:10Z' }})
        a.save()
        
        class A2(Document):
            d = DictProperty()
        a2 = A2()            
        self.assertTrue(a2.validate(required=False))
        self.assertTrue(a2.validate())
        
    def testDynamicDictProperty(self):
        from datetime import datetime
        class A(Document):
            pass
            
        a = A()
        a.d = {}
        
        a.d['test'] = { 'a': datetime(2009, 5, 10, 21, 19, 21, 127380) }
        self.assert_(a.d == {'test': {'a': datetime(2009, 5, 10, 21, 19, 21, 127380)}})
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z'}}, 'doc_type': 'A'} )
        
        a.d['test']['b'] = "essai"
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['essai'] = "test"
        self.assert_(a.d == {'essai': 'test',
         'test': {'a': datetime(2009, 5, 10, 21, 19, 21, 127380),
                  'b': 'essai'}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}},
         'doc_type': 'A'})
         
        del a.d['test']['a']
        self.assert_(a.d == {'essai': 'test', 'test': {'b': 'essai'}})
        self.assert_(a._doc ==  {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['test']['essai'] = { "a": datetime(2009, 5, 10, 21, 21, 11, 425782) }
        self.assert_(a.d == {'essai': 'test',
         'test': {'b': 'essai',
                  'essai': {'a': datetime(2009, 5, 10, 21, 21, 11, 425782)}}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test',
               'test': {'b': 'essai', 'essai': {'a': '2009-05-10T21:21:11Z'}}},
         'doc_type': 'A'}
        )
        
        del a.d['test']['essai']
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
    def testDynamicDictProperty2(self):
        from datetime import datetime
        class A(Document):
            pass
        
        A.set_db(self.db)
        
        a = A()
        a.s = "test"
        a.d = {}
        a.d['s'] = "level1"
        a.d['d'] = {}
        a.d['d']['s'] = "level2"
        self.assert_(a._doc == {'d': {'d': {'s': 'level2'}, 's': 'level1'}, 'doc_type': 'A', 's': u'test'})
        a.save()
        
        a1 = A.get(a._id)
        a1.d['d']['s'] = "level2 edited"
        self.assert_(a1.d['d']['s'] == "level2 edited")

        self.assert_(a1._doc['d']['d']['s'] == "level2 edited")
        
        class A2(Document):
            pass
        A2.set_db(self.db) 
        a = A2(l=["a", "b", "c"])
        a.save()
        b = self.db.get(a._id, wrapper=A2.wrap)
        self.assert_(b.l == ["a", "b", "c"])
        b.l = []
        self.assert_(b.l == [])
        self.assert_(b.to_json()['l'] == [])
        
    def testDynamicListProperty(self):
        from datetime import datetime
        class A(Document):
            pass
        
        A.set_db(self.db)
        
        a = A()
        a.l = []
        a.l.append(1)
        a.l.append(datetime(2009, 5, 12, 13, 35, 9, 425701))
        a.l.append({ 's': "test"})
        self.assert_(a.l == [1, datetime(2009, 5, 12, 13, 35, 9, 425701), {'s': 'test'}])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [1, '2009-05-12T13:35:09Z', {'s': 'test'}]}
        )
        a.l[2]['date'] = datetime(2009, 5, 12, 13, 35, 9, 425701)
        self.assert_(a._doc == {'doc_type': 'A',
         'l': [1,
               '2009-05-12T13:35:09Z',
               {'date': '2009-05-12T13:35:09Z', 's': 'test'}]}
        )
        a.save()
        
        a1 = A.get(a._id)
        self.assert_(a1.l == [1,
         datetime(2009, 5, 12, 13, 35, 9),
         {u'date': datetime(2009, 5, 12, 13, 35, 9), u's': u'test'}]
        )
        
        a.l[2]['s'] = 'test edited'
        self.assert_(a.l == [1,
         datetime(2009, 5, 12, 13, 35, 9, 425701),
         {'date': datetime(2009, 5, 12, 13, 35, 9, 425701),
          's': 'test edited'}]
        )
        self.assert_(a._doc['l'] == [1,
         '2009-05-12T13:35:09Z',
         {'date': '2009-05-12T13:35:09Z', 's': 'test edited'}]
        )
        
        
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "A") { emit(doc._id, doc);
}}"""
                }
            }
        }
        self.db.save_doc(design_doc)
        
        a2 = A()
        a2.l = []
        a2.l.append(7)
        a2.save()
        docs = A.view('test/all')
        self.assert_(len(docs) == 2)
        
        a3 = A()
        a3.l = []
        a3.save()
        docs = A.view('test/all')
        self.assert_(len(docs) == 3)
        
        a = A(l = [1, 2])
        self.assert_(a.l == [1,2])
        self.assert_(a._doc['l'] == [1,2])
        
        a = A()
        a.l = [1, 2]
        self.assert_(a.l == [1,2])
        self.assert_(a._doc['l'] == [1,2])
        

        class A2(Document):
            pass
        A2.set_db(self.db) 
        a = A2(d={"a": 1, "b": 2, "c": 3})
        a.save()
        b = self.db.get(a._id, wrapper=A2.wrap)
        self.assert_(b.d == {"a": 1, "b": 2, "c": 3})
        b.d = {}
        self.assert_(b.d == {})
        self.assert_(b.to_json()['d'] == {})
        
if __name__ == '__main__':
    unittest.main()
