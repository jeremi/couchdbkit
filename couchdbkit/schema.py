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

""" module that provide a Document object that allow you 
to map statically, dynamically or both a CouchDB
document in python """

import datetime
import decimal
import re
import warnings

from couchdbkit.client import Database
from couchdbkit import properties as p
from couchdbkit.properties_map import value_to_json, value_to_python, convert_property, MAP_TYPES_PROPERTIES
from couchdbkit.exceptions import *
from couchdbkit.resource import ResourceNotFound


__all__ = ['ReservedWordError', 'ALLOWED_PROPERTY_TYPES', 'DocumentSchema', 
        'SchemaProperties', 'DocumentBase', 'QueryMixin', 'AttachmentMixin', 
        'Document', 'StaticDocument']

_RESERVED_WORDS = ['_id', '_rev', '$schema']

_NODOC_WORDS = ['doc_type','id', 'rev']


ALLOWED_PROPERTY_TYPES = set([
    basestring,
    str,
    unicode,
    bool,
    int,
    long,
    float,
    datetime.datetime,
    datetime.date,
    datetime.time,
    decimal.Decimal,
    dict,
    list,
    type(None)
])



def check_reserved_words(attr_name):
    if attr_name in _RESERVED_WORDS:
        raise ReservedWordError(
            "Cannot define property using reserved word '%(attr_name)s'." % 
            locals())



class SchemaProperties(type):

    def __new__(cls, name, bases, attrs):
        # init properties
        properties = {}
        defined = set()
        for base in bases:
            if hasattr(base, '_properties'):
                property_keys = base._properties.keys()
                duplicate_properties = defined.intersection(property_keys)
                if duplicate_properties:
                    raise DuplicatePropertyError(
                        'Duplicate properties in base class %s already defined: %s' % (base.__name__, list(duplicate_properties)))
                defined.update(property_keys)
                properties.update(base._properties) 
                
        doc_type = attrs.get('doc_type', False)
        if not doc_type:
            doc_type = name
        else:
            del attrs['doc_type']
            
        attrs['_doc_type'] = doc_type
                
        for attr_name, attr in attrs.items():
            # map properties
            if isinstance(attr, p.Property):
                check_reserved_words(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
            # python types
            elif type(attr) in MAP_TYPES_PROPERTIES and \
                    not attr_name.startswith('_') and \
                    attr_name not in _NODOC_WORDS:
                check_reserved_words(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                prop = MAP_TYPES_PROPERTIES[type(attr)](default=attr)
                properties[attr_name] = prop
                prop.__property_config__(cls, attr_name)
                attrs[attr_name] = prop

        attrs['_properties'] = properties
        return type.__new__(cls, name, bases, attrs)        


class DocumentSchema(object):
    __metaclass__ = SchemaProperties
    
    _dynamic_properties = None
    _allow_dynamic_properties = True
    _doc = None
    _db = None
    
    def __init__(self, d=None, **properties):
        self._dynamic_properties = {} 
        self._doc = {}

        if d is not None:
            if not isinstance(d, dict):
                raise TypeError('d should be a dict')
            properties.update(d)
            
        doc_type = getattr(self, '_doc_type', self.__class__.__name__)
        self._doc['doc_type'] = doc_type
           
        for prop in self._properties.values():
            if prop.name in properties:
                value = properties.pop(prop.name)
                if value is None:
                    value = prop.default_value()
            else:
                value = prop.default_value()
            prop.__property_init__(self, value)

        _dynamic_properties = properties.copy()
        for attr_name, value in _dynamic_properties.iteritems():
            if attr_name not in self._properties \
                    and value is not None:
                if isinstance(value, p.Property):
                    value.__property_config__(self, attr_name)
                    value.__property_init__(self, value.default_value())
                elif isinstance(value, DocumentSchema):
                    from couchdbkit.schema import SchemaProperty
                    value = SchemaProperty(value)
                    value.__property_config__(self, attr_name)
                    value.__property_init__(self, value.default_value())

                
                setattr(self, attr_name, value)
                # remove the kwargs to speed stuff
                del properties[attr_name]


    def dynamic_properties(self):
        if self._dynamic_properties is None:
            return {}
        return self._dynamic_properties

    def properties(self):
        return self._properties

    def all_properties(self):
        all_properties = self._properties
        all_properties.update(self.dynamic_properties())
        return all_properties

    def to_json(self):
        if self._doc.get('doc_type') is None:
            doc_type = getattr(self, '_doc_type', self.__class__.__name__)
            self._doc['doc_type'] = doc_type
        return self._doc

    
    def __setattr__(self, key, value):
        check_reserved_words(key)
        if not hasattr( self, key ) and not self._allow_dynamic_properties:
            raise AttributeError("%s is not defined in schema (not a valid property)" % key)
            
        if not key.startswith('_') and \
                key not in self._properties and \
                key not in dir(self): 
            if type(value) not in ALLOWED_PROPERTY_TYPES and \
                    not isinstance(value, (p.Property,)):
                raise TypeError("Document Schema cannot accept values of type '%s'." %
                        type(value).__name__)
            
            if self._dynamic_properties is None:
                self._dynamic_properties = {}

            self._dynamic_properties[key] = value

            if not isinstance(value, (p.Property,)):
                if callable(value):
                    value = value()
                self._doc[key] = convert_property(value)
        else:
            object.__setattr__(self, key, value)

    def __delattr__(self, key):
        """ delete property
        """
        if key in self._doc:
            del self._doc[key]

        if self._dynamic_properties and key in self._dynamic_properties:
            del self._dynamic_properties[key]
        else:
            object.__delattr__(self, key)

    def __getattr__(self, key):
        """ get property value 
        """
        if self._dynamic_properties and key in self._dynamic_properties:
            return self._dynamic_properties[key]
        return getattr(super(DocumentSchema, self), key)
    
    def __getitem__(self, key):
        """ get property value
        """
        try:
            return getattr(self, key)
        except AttributeError, e:
            if key in self._doc:
                return self._doc[key]
            raise KeyError, e
        except:
            raise

    def __setitem__(self, key, value):
        """ add a property
        """
        try:
            setattr(self, key, value)
        except AttributeError, e:
            raise KeyError, e

    def __delitem__(self, key):
        """ delete a property
        """ 
        try:
            delattr(self, key)
        except AttributeError, e:
            raise KeyError, e


    def __contains__(self, key):
        """ does object contain this propery ?

        :param key: name of property
        
        :return: True if key exist.
        """ 
        if key in self.all_properties():
            return True
        elif key in self._doc:
            return True
        return False

    def __iter__(self):
        """ iter document instance properties
        """

        all_properties = self.all_properties()

        for prop, value in all_properties.iteritems():
            if value is not None:
                yield (prop, value)

    def items(self):
        """ return list of items
        """
        return list(self)

    def __len__(self):
        """ get number of properties
        """
        return len(self._doc or ())

    def __getstate__(self):
        """ let pickle play with us """
        obj_dict = self.__dict__.copy()
        return obj_dict

    @classmethod
    def wrap(cls, data):
        instance = cls()
        
        instance._doc = data

        for prop in instance._properties.values():
            if prop.name in data:
                value = data[prop.name]
                if value is not None:
                    value = prop.to_python(value)
                else:
                    value = prop.default_value()
            else:
                value = prop.default_value()
            prop.__property_init__(instance, value)
            
        if cls._allow_dynamic_properties:
            for attr_name, value in data.iteritems():
                if attr_name in instance._properties:
                    continue
                if value is None:
                    continue
                elif attr_name in ('_rev', '_id', 'doc_type'):
                    continue
                elif type(value) in MAP_TYPES_PROPERTIES and \
                        not attr_name.startswith('_') and \
                        attr_name not in _NODOC_WORDS:
                
                    value = value_to_python(value)
                    setattr(instance, attr_name, value)
        
        return instance

    def validate(self, required=True):
        """ validate a document """
        for attr_name, value in self._doc.items():
            if attr_name in self._properties:
                self._properties[attr_name].validate(
                        getattr(self, attr_name), required=required)
   
    def clone(self, **kwargs):
        for prop_name in self._properties.keys():
            try:
                kwargs[prop_name] = self._doc[prop_name]
            except KeyError:
                pass

        kwargs.update(self._dynamic_properties)
        obj = type(self)(**kwargs)
        obj._doc = self._doc
 
        return obj

    @classmethod
    def build(cls, **kwargs):
        obj = cls()
        properties = {}
        for attr_name, attr in kwargs.items():
            if isinstance(attr, (p.Property,)):
                properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
            elif type(attr) in MAP_TYPES_PROPERTIES and \
                    not attr_name.startswith('_') and \
                    attr_name not in _NODOC_WORDS:
                check_reserved_words(attr_name)
                
                prop = MAP_TYPES_PROPERTIES[type(attr)](default=attr)
                properties[attr_name] = prop
                prop.__property_config__(cls, attr_name)
                attrs[attr_name] = prop
        return type('AnonymousSchema', (cls,), properties)

class DocumentBase(DocumentSchema):
    """ Base Document object that map a CouchDB Document.
    It allow you to map statically a document by 
    providing fields like you do with any ORM or
    dynamically. Ie unknown fields are loaded as
    object property that you can edit, datetime in
    iso3339 format are automatically translated in
    python types (date, time & datetime) and decimal too.

    Example of documentass

    .. code-block:: python
        
        from couchdbkit.schema import *
        class MyDocument(Document):
            mystring = StringProperty()
            myotherstring = unicode() # just use python types


    Fields of a documents can be accessed as property or
    key of dict. These are similar : ``value = instance.key or value = instance['key'].``

    To delete a property simply do ``del instance[key'] or delattr(instance, key)``
    """
    _db = None

    def __init__(self, d=None, **kwargs):
        if 'id' in kwargs:
            self._doc['_id'] = kwargs.pop('_id')
        DocumentSchema.__init__(self, d, **kwargs) 
    
    def get_id(self):
        return self._doc.get('_id', None)

    def set_id(self, docid):
        if not isinstance(docid, basestring):
            raise TypeError('doc id should be a string')
        self._doc['_id'] = docid
    id = property(get_id, set_id)

    rev = property(lambda self: self._doc.get('_rev'))

    @classmethod
    def set_db(cls, db):
        """ Set document db"""
        cls._db = db
        
    @classmethod
    def get_db(cls):
        """ get document db"""
        db = getattr(cls, '_db', None)
        if db is None:
            raise TypeError("doc database required to save document")
        return db
    
    def save(self):
        """ Save document in database.
            
        :params db: couchdbkit.core.Database instance
        """
        self.validate()    
        if self._db is None:
            raise TypeError("doc database required to save document")
        
        doc = self.to_json()
        self._db.save_doc(doc)
        self._doc.update({'_id': doc['_id'], '_rev': doc['_rev']})
        
    store = save
    
    @classmethod
    def get(cls, docid, rev=None, db=None, dynamic_properties=True):
        if db is not None:
            cls._db = db
        cls._allow_dynamic_properties = dynamic_properties
        if cls._db is None:
            raise TypeError("doc database required to save document")
        return cls._db.get(docid, rev=rev, wrapper=cls.wrap)
        
    @classmethod
    def get_or_create(cls, docid=None, db=None, dynamic_properties=True):
        if db is not None:
            cls._db = db
               
        cls._allow_dynamic_properties = dynamic_properties
        
        if cls._db is None:    
            raise TypeError("doc database required to save document")
            
        if docid is None:
            obj = cls()
            obj.save()
            return obj
        
        try:
            return cls._db.get(docid, wrapper=cls.wrap)
        except ResourceNotFound:
            obj = cls()
            obj.id = docid
            obj.save()
            return obj
  
    new_document = property(lambda self: self._doc.get('_rev') is None) 
    
class AttachmentMixin(object):
    """
    mixin to manage attachments of a doc.
    
    """
    
    def put_attachment(self, content, name=None,
        content_type=None, content_length=None):
        """ Add attachement to a document.
 
        :param content: string or :obj:`File` object.
        :param name: name or attachment (file name).
        :param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        :param content_lenght: int, size of attachment.

        :return: bool, True if everything was ok.
        """
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        return self.__class__._db.put_attachment(self, content, name=name,
            content_type=content_type, content_length=content_length)

    def delete_attachment(self, name):
        """ delete attachement of documen
        
        :param name: name of attachement
    
        :return: dict, withm member ok setto True if delete was ok.
        """
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        return self.__class__._db.delete_attachment(self, name)

    def fetch_attachment(self, name):
        """ get attachment in document
        
        :param name: name of attachment default: default result

        :return: str or unicode, attachment
        """
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        return self.__class__._db.fetch_attachment(self, name)
        
        
class QueryMixin(object):
    """ Mixin that add query methods """
    
    @classmethod
    def __view(cls, view_type=None, data=None, wrapper=None, dynamic_properties=True, **params):
        def default_wrapper(row):
            data = row.get('value')
            docid = row.get('id')

            if not data or data is None:
                doc = row.get('doc', False)
                if doc:
                    return cls.wrap(doc)
                return row
                
            if not isinstance(data, dict) or not docid:
                return row
                
            data['_id'] = docid
            cls._allow_dynamic_properties = dynamic_properties
            obj = cls.wrap(data)
            return obj
        
        if wrapper is None:
            wrapper = default_wrapper
            
        if not wrapper:
            wrapper = None
        elif not callable(wrapper):
            raise TypeError("wrapper is not a callable")
        
        db = cls.get_db()
        if view_type == 'view':
            return db.view(data, wrapper=wrapper, **params)
        elif view_type == 'temp_view':
            return db.temp_view(data, wrapper=wrapper, **params)    
        else:
            raise RuntimeError("bad view_type : %s" % view_type )
            
    @classmethod
    def view(cls, view_name, wrapper=None, dynamic_properties=True, **params):
        """ Get documents associated to a view.
        Results of view are automatically wrapped
        to Document object.

        :params view_name: str, name of view
        :params params:  params of view

        :return: :class:`simplecouchdb.core.ViewResults` instance. All
        results are wrapped to current document instance.
        """
        return cls.__view(view_type="view", data=view_name, wrapper=wrapper, dynamic_properties=dynamic_properties, **params) 
        
    @classmethod
    def temp_view(cls, design, wrapper=None, dynamic_properties=True, **params):
        """ Slow view. Like in view method,
        results are automatically wrapped to 
        Document object.

        :params design: design object, See `simplecouchd.client.Database`
        :params params:  params of view

        :return: Like view, return a :class:`simplecouchdb.core.ViewResults` instance. All
        results are wrapped to current document instance.
        """
        return cls.__view(view_type="temp_view", data=design, wrapper=wrapper, dynamic_properties=dynamic_properties, **params) 
        
class Document(DocumentBase, QueryMixin, AttachmentMixin):
    """
    Full featured document object implementing the following :
    
    :class:`QueryMixin` for view & temp_view that wrap results to this object
    :class `AttachmentMixin` for attachments function
    """ 

class StaticDocument(Document):
    """
    Shorthand for a document that disallow dynamic properties.
    """
    _allow_dynamic_properties = False
