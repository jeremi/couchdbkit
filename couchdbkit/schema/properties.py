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


from calendar import timegm
import decimal
import datetime
import re
import time

from couchdbkit.exceptions import *

__all__ = ['ALLOWED_PROPERTY_TYPES', 'Property', 'StringProperty', 
        'IntegerProperty','DecimalProperty', 'BooleanProperty', 
        'FloatProperty','DateTimeProperty', 'DateProperty', 
        'TimeProperty','DictProperty', 'ListProperty', 
        'StringListProperty', 'dict_to_json', 'list_to_json', 
        'value_to_json', 'MAP_TYPES_PROPERTIES', 'value_to_python', 
        'dict_to_python', 'list_to_python', 'convert_property',
        'value_to_property', 'LazyDict', 'LazyList']
        
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

re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
re_time = re.compile('^([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?$')
re_datetime = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?([zZ]|([\+-])([01]\d|2[0-3])\D?([0-5]\d)?)?)?$')
re_decimal = re.compile('^(\d+).(\d+)$')

class Property(object):
    """ Property base which all other properties
    inherit."""
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None, 
            default=None, required=False, validators=None,
            choices=None):
        """ Default constructor for a property. 

        :param verbose_name: str, verbose name of field, could
                be use for description
        :param name: str, name of field
        :param default: default value
        :param required: True if field is required, default is False
        :param validators: list of callable or callable, field validators 
        function that are executed when document is saved.
        """
        self.verbose_name = verbose_name
        self.name = name
        self.default = default
        self.required = required
        self.validators = validators
        self.choices = choices
        Property.creation_counter += 1

    def __property_config__(self, document_class, property_name):
        self.document_class = document_class
        if self.name is None:
            self.name = property_name

    def __property_init__(self, document_instance, value):
        """ method used to set value of the property when
        we create the document. Don't check required. """
        if value is not None:
            value = self.to_json(self.validate(value, required=False))
        document_instance._doc[self.name] = value

    def __get__(self, document_instance, document_class):
        if document_instance is None:
            return self

        value = document_instance._doc.get(self.name)
        if value is not None:
            value = self.to_python(value)
        
        return value

    def __set__(self, document_instance, value):
        value = self.validate(value, required=False)
        document_instance._doc[self.name] = self.to_json(value)

    def __delete__(self, document_instance):
        pass

    def default_value(self):
        """ return default value """

        default = self.default
        if callable(default):
            default = default()
        return default

    def validate(self, value, required=True):
        """ validate value """
        if required and self.empty(value):
            if self.required:
                raise BadValueError("Property %s is required." % self.name)
        else:
            if self.choices:
                match = False
                for choice in self.choices:
                    if choice == value:
                        match = True
                    if not match:
                        raise BadValueError('Property %s is %r; must be one of %r' % (
                            self.name, value, self.choices))
        if self.validators:
            if isinstance(self.validators, (list, tuple,)):
                for validator in self.validators:
                    if callable(validator):
                        validator(value)
            elif callable(self.validators):
                self.validators(value)
        return value

    def empty(self, value):
        """ test if value is empty """
        return not value or value is None

    def to_python(self, value):
        """ convert to python type """
        return unicode(value)

    def to_json(self, value):
        """ convert to json, These converetd value is saved in couchdb. """
        return self.to_python(value)

    data_type = None

class StringProperty(Property):
    """ string property str or unicode property 
    
    *Value type*: unicode
    """

    to_python = unicode 

    def validate(self, value, required=True):
        value = super(StringProperty, self).validate(value,
                required=required)

        if value is None:
            return value
        
        if not isinstance(value, basestring):
            raise BadValueError(
                'Property %s must be unicode or str instance, not a %s' % (self.name, type(value).__name__))
        return value

    data_type = unicode

class IntegerProperty(Property):
    """ Integer property. map to int 
    
    *Value type*: int
    """
    to_python = int

    def empty(self, value):
        return value is None

    def validate(self, value, required=True):
        value = super(IntegerProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if value is not None and not isinstance(value, (int, long,)):
            raise BadValueError(
                'Property %s must be %s or long instance, not a %s'
                % (self.name, type(self.data_type).__name__, 
                    type(value).__name__)) 

        return value 

    data_type = int
LongProperty = IntegerProperty

class FloatProperty(Property):
    """ Float property, map to python float 
    
    *Value type*: float
    """
    to_python = float
    data_type = float

    def validate(self, value, required=True):
        value = super(FloatProperty, self).validate(value, 
                required=required)

        if value is None:
            return value

        if not isinstance(value, float):
            raise BadValueError(
                'Property %s must be float instance, not a %s'
                % (self.name, type(value).__name__))
        
        return value
Number = FloatProperty

class BooleanProperty(Property):
    """ Boolean property, map to python bool
    
    *ValueType*: bool
    """
    to_python = bool
    data_type = bool

    def validate(self, value, required=True):
        value = super(BooleanProperty, self).validate(value, 
                required=required)

        if value is None:
            return value

        if value is not None and not isinstance(value, bool):
            raise BadValueError(
                'Property %s must be bool instance, not a %s'
                % (self.name, type(value).__name__))
        
        return value

class DecimalProperty(Property):
    """ Decimal property, map to Decimal python object
    
    *ValueType*: decimal.Decimal
    """
    data_type = decimal.Decimal

    def to_python(self, value):
        return decimal.Decimal(value)

    def to_json(self, value):
        return unicode(value)

class DateTimeProperty(Property):
    """DateTime property. It convert iso3339 string
    to python and vice-versa. Map to datetime.datetime
    object.
    
    *ValueType*: datetime.datetime
    """

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False,
               **kwds):
        super(DateTimeProperty, self).__init__(verbose_name, **kwds)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def validate(self, value, required=True):
        value = super(DateTimeProperty, self).validate(value, required=required)

        if value is None:
            return value

        if value and not isinstance(value, self.data_type):
            raise BadValueError('Property %s must be a %s, current is %s' %
                          (self.name, self.data_type.__name__, type(value).__name__))
        return value

    def default_value(self):
        if self.auto_now or self.auto_now_add:
            return self.now()
        return Property.default_value(self)

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = value.rstrip('Z') # remove timezone separator
                timestamp = timegm(time.strptime(value, '%Y-%m-%dT%H:%M:%S'))
                value = datetime.datetime.utcfromtimestamp(timestamp)
            except ValueError, e:
                raise ValueError('Invalid ISO date/time %r' % value)
        return value

    def to_json(self, value):
        if self.auto_now:
            value = self.now()
        return value.replace(microsecond=0).isoformat() + 'Z'

    data_type = datetime.datetime

    @staticmethod
    def now():
        return datetime.datetime.utcnow()

class DateProperty(DateTimeProperty):
    """ Date property, like DateTime property but only
    for Date. Map to datetime.date object
    
    *ValueType*: datetime.date
    """
    data_type = datetime.date

    @staticmethod
    def now():
        return datetime.datetime.now().date()

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = datetime.date(*time.strptime(value, '%Y-%m-%d')[:3])
            except ValueError, e:
                raise ValueError('Invalid ISO date %r' % value)
        return value

    def to_json(self, value):
        return value.isoformat()

class TimeProperty(DateTimeProperty):
    """ Date property, like DateTime property but only
    for time. Map to datetime.time object
    
    *ValueType*: datetime.time
    """

    data_type = datetime.time

    @staticmethod
    def now(self):
        return datetime.datetime.now().time()

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = datetime.time(*time.strptime(value, '%H:%M:%S')[3:6])
            except ValueError, e:
                raise ValueError('Invalid ISO time %r' % value)
        return value

    def to_json(self, value):
        return value.replace(microsecond=0).isoformat()
        

class DictProperty(Property):
    """ A property that stores a dict of things"""
    
    def __init__(self, verbose_name=None, default=None, 
        required=False, **kwds):
        """
        :args verbose_name: Optional verbose name.
        :args default: Optional default value; if omitted, an empty list is used.
        :args**kwds: Optional additional keyword arguments, passed to base class.

        Note that the only permissible value for 'required' is True.
        """
           
        if default is None:
            default = {}
            
        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)
            
    data_type = dict
    
    def validate(self, value, required=True):
        value = super(DictProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, dict):
                raise BadValueError('Property %s must be a dict' % self.name)
            value = self.validate_dict_contents(value)
        return value
        
    def validate_dict_contents(self, value):
        try:
            value = validate_dict_content(value)
        except BadValueError:
            raise BadValueError(
                'Items of %s dict must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value
        
    def default_value(self):
        """Default value for list.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(DictProperty, self).default_value()
        if value is None:
            value = {}
        return dict(value)
        
    def to_python(self, value):
        return LazyDict(value_to_python(value), value)
        
    def to_json(self, value):
        return value_to_json(value)
        
        

class ListProperty(Property):
    """A property that stores a list of things.

      """
    def __init__(self, verbose_name=None, default=None, 
            required=False, item_type=None, **kwds):
        """Construct ListProperty.

    
         :args verbose_name: Optional verbose name.
         :args default: Optional default value; if omitted, an empty list is used.
         :args**kwds: Optional additional keyword arguments, passed to base class.

        Note that the only permissible value for 'required' is True.
        
        """
        if default is None:
            default = []
            
        if item_type is not None and item_type not in ALLOWED_PROPERTY_TYPES:
            raise ValueError('item_type %s not in %s' % (item_type, ALLOWED_PROPERTY_TYPES))
        self.item_type = item_type

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)
        
    data_type = list
        
    def validate(self, value, required=True):
        value = super(ListProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, list):
                raise BadValueError('Property %s must be a list' % self.name)
            value = self.validate_list_contents(value)
        return value
        
    def validate_list_contents(self, value):
        value = validate_list_content(value, item_type=self.item_type)
        try:
            value = validate_list_content(value, item_type=self.item_type)
        except BadValueError:
            raise BadValueError(
                'Items of %s list must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value
        
    def default_value(self):
        """Default value for list.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(ListProperty, self).default_value()
        if value is None:
            value = []
        return list(value)
        
    def to_python(self, value):
        return LazyList(value_to_python(value), value)
        
    def to_json(self, value):
        return value_to_json(value)


class StringListProperty(ListProperty):
    """ shorthand for list that should containe only str"""
    
    def __init__(self, verbose_name=None, default=None, 
            required=False, **kwds):
        super(StringListProperty, self).__init__(verbose_name=verbose_name, 
            default=default, required=required, item_type=str,**kwds)



# structures proxy

class LazyDict(dict):
    
    """ object to make sure we keep update of dict 
    in _doc. We just override a dict and maintain change in
    doc reference (doc[keyt] obviously).
    """

    def __init__(self, d, doc):
        dict.__init__(self)
        d = d or {}
        self.doc = doc
        for key, value in d.items():
            self[key] = value

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self.doc[key] = {}
            value = LazyDict(value,  self.doc[key])
        elif isinstance(value, list):
            value = LazyList(value,  self.doc[key])
        else:
            self.doc.update({key: value_to_json(value) })
        super(LazyDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        del self.doc[key]
        super(LazyDict, self).__delitem__(key)

    def pop(self, key, default=None):
        del self.doc[key]
        return super(LazyDict, self).pop(key, default=default)

    def setdefault(self, key, default):
        if key in self:
            return self[key]  
        self.doc.setdefault(key, value_to_json(default))
        super(LazyDict, self).setdefault(key, default)
        return default

    def update(self, value):
        for k, v in value.items():
            self[k] = v

    def popitem(self, value):
        new_value = super(LazyDict, self).popitem(value)
        self.doc.popitem(value_to_json(value))
        return new_value

    def clear(self):
        self.doc.clear()
        super(LazyDict, self).clear()

class LazyList(list):
    """ object to make sure we keep update of list 
    in _doc. We just override a dict and maintain change in
    doc reference (doc[keyt] obviously).
    """

    def __init__(self, l, doc):
        l = l or []
        list.__init__(self, l)
        self.doc = doc
        for idx, item in enumerate(l):
            self[idx] = item
        
    def __delitem__(self, index):
        del self.doc[index]
        list.__delitem__(self, index)

    def __setitem__(self, index, value):
        if isinstance(value, dict):
            self.doc[index] = {}
            value = LazyDict(value, self.doc[index])
        elif isinstance(value, list):
            self.doc[index] = []
            value = LazyList(value, self.doc[index])
        else:
            self.doc[index] = value_to_json(value)
        list.__setitem__(self, index, value)

    def append(self, *args, **kwargs):
        if args:
            assert len(args) == 1
            value = args[0]
        else:
            value = kwargs

        index = len(self)
        if isinstance(value, dict):
            self.doc.append({})
            value = LazyDict(value, self.doc[index])
        elif isinstance(value, list):
            self.doc.append([])
            value = LazyList(value, self.doc[index])
        else:
            self.doc.append(value_to_json(value))
        super(LazyList, self).append(value)

# some mapping
 
MAP_TYPES_PROPERTIES = {
        decimal.Decimal: DecimalProperty,
        datetime.datetime: DateTimeProperty,
        datetime.date: DateProperty,
        datetime.time: TimeProperty,
        str: StringProperty,
        unicode: StringProperty,
        bool: BooleanProperty,
        int: IntegerProperty,
        long: LongProperty,
        float: FloatProperty,
        list: ListProperty,
        dict: DictProperty
}           
            
def convert_property(value):
    """ convert a value to json from Property._to_json """
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        value = prop.to_json(value)
    return value


def value_to_property(value):
    """ Convert value in a Property object """
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        return prop
    else:
        return value

# utilities functions

def validate_list_content(value, item_type=None):
    """ validate type of values in a list """
    return [validate_content(item, item_type=item_type) for item in value]
    
def validate_dict_content(value, item_type=None):
     """ validate type of values in a dict """
    return dict([(k, validate_content(v, 
                item_type=item_type)) for k, v in value.iteritems()])
           
def validate_content(value, item_type=None):
    """ validate a value. test if value is in supported types """
    if isinstance(value, list):
        value = validate_list_content(value, item_type=item_type)
    elif isinstance(value, dict):
        value = validate_dict_content(value, item_type=item_type)
    elif item_type is not None and type(value) != item_type:
        raise BadValueError(
            'Items  must all be in %s' % item_type)
    elif type(value) not in ALLOWED_PROPERTY_TYPES:
            raise BadValueError(
                'Items  must all be in %s' %
                    (ALLOWED_PROPERTY_TYPES))
    return value

def dict_to_json(value):
    """ convert a dict to json """
    return dict([(k, value_to_json(v)) for k, v in value.iteritems()])
    
def list_to_json(value):
    """ convert a list to json """
    return [value_to_json(item) for item in value]
    
def value_to_json(value):
    """ convert a value to json using appropriate regexp.
    For Dates we use ISO 8601. Decimal are converted to string.
    
    """
    if isinstance(value, datetime.datetime):
        value = value.replace(microsecond=0).isoformat() + 'Z'
    elif isinstance(value, datetime.date):
        value = value.isoformat()
    elif isinstance(value, datetime.time):
        value = value.replace(microsecond=0).isoformat()
    elif isinstance(value, decimal.Decimal):
        value = unicode(value) 
    elif isinstance(value, list):
        value = list_to_json(value)
    elif isinstance(value, dict):
        value = dict_to_json(value)
    return value
    
    
def value_to_python(value):
    """ convert a json value to python type using regexp. values converted
    have been put in json via `value_to_json` .
    """
    data_type = None
    if isinstance(value, basestring):
        if re_date.match(value):
            data_type = datetime.date
        elif re_time.match(value):
            data_type = datetime.time
        elif re_datetime.match(value):
            data_type = datetime.datetime
        elif re_decimal.match(value):
            data_type = decimal.Decimal
        if data_type is not None:
            prop = MAP_TYPES_PROPERTIES[data_type]()
            try: 
                #sometimes regex fail so return value
                value = prop.to_python(value)
            except:
                pass           
    elif isinstance(value, list):
        value = list_to_python(value)
    elif isinstance(value, dict):
        value = dict_to_python(value)
    return value
    
def list_to_python(value):
    """ convert a list of json values to python list """
    return [value_to_python(item) for item in value]
    
def dict_to_python(value):
     """ convert a json object values to python dict """
    return dict([(k, value_to_python(v)) for k, v in value.iteritems()])