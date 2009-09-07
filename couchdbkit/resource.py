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

""" 
couchdb.resource
~~~~~~~~~~~~~~~~~~~~~~

This module providess a common interface for all CouchDB request. This
module makes HTTP request using :mod:`httplib2` module or :mod:`pycurl` 
if available. Just use set transport argument for this.

Example: 
    
    >>> resource = CouchdbResource()
    >>> info = resource.get()
    >>> info['couchdb']
    u'Welcome'

"""

import httplib
import restkit
from restkit.httpc import HTTPResponse

import socket
import sys
import time
import types

import anyjson
        
from couchdbkit import __version__

USER_AGENT = 'couchdbkit/%s' % __version__

class ResourceConflict(restkit.ResourceError):
    """ Exception raised when there is conflict while updating"""

class PreconditionFailed(restkit.ResourceError):
    """ Exception raised when 412 HTTP error is received in response
    to a request """

ResourceNotFound = restkit.ResourceNotFound

class CouchdbResource(restkit.Resource):

    def __init__(self, uri="http://127.0.0.1:5984", transport=None):
        """Constructor for a `CouchdbResource` object.

        CouchdbResource represent an HTTP resource to CouchDB.

        @param uri: str, full uri to the server.
        @param transport: any http instance of object based on 
                `restkit.transport.HTTPTransportBase`. By 
                default it will use a client based on 
                `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or `restkit.transport.HTTPLib2Transport`,
                a client based on `Httplib2 <http://code.google.com/p/httplib2/>`_ 
                or make your own depending on the options you need to access the 
                server (authentification, proxy, ....).
        """
        
        restkit.Resource.__init__(self, uri=uri, transport=transport)
        self.client.safe = ":/"

    def copy(self, path=None, headers=None, **params):
        """ add copy to HTTP verbs """
        return self.request('COPY', path=path, headers=headers, **params)
        
    def request(self, method, path=None, payload=None, headers=None, 
         _stream=False, _stream_size=16384, **params):
        """ Perform HTTP call to the couchdb server and manage 
        JSON conversions, support GET, POST, PUT and DELETE.
        
        Usage example, get infos of a couchdb server on 
        http://127.0.0.1:5984 :


            import couchdbkit.CouchdbResource
            resource = couchdbkit.CouchdbResource()
            infos = resource.request('GET'))

        @param method: str, the HTTP action to be performed: 
            'GET', 'HEAD', 'POST', 'PUT', or 'DELETE'
        @param path: str or list, path to add to the uri
        @param data: str or string or any object that could be
            converted to JSON.
        @param headers: dict, optionnal headers that will
            be added to HTTP request.
        @param _stream: boolean, response return a ResponseStream object
        @param _stream_size: int, size in bytes of response stream block
        @param params: Optionnal parameterss added to the request. 
            Parameterss are for example the parameters for a view. See 
            `CouchDB View API reference 
            <http://wiki.apache.org/couchdb/HTTP_view_API>`_ for example.
        
        @return: tuple (data, resp), where resp is an `httplib2.Response` 
            object and data a python object (often a dict).
        """
        
        headers = headers or {}
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('User-Agent', USER_AGENT)

        # always init url safe chars
        self.client.safe=":/"
        if path is not None  and "%" in path: 
            # we already encode some parts of url
            self.client.safe = ":/%"

        body = None
        if payload is not None:
            #TODO: handle case we want to put in payload json file.
            if not hasattr(payload, 'read') and not isinstance(payload, basestring):
                body = anyjson.serialize(payload).encode('utf-8')
                headers.setdefault('Content-Type', 'application/json')
            else:
                body = payload

        params = self.encode_params(params)

        def _make_request(retry=1):
            try:
                return restkit.Resource.request(self, method, path=path,
                        payload=body, headers=headers, _stream=_stream, 
                        _stream_size=_stream_size, **params)
            except (socket.error, httplib.BadStatusLine), e:
                if retry > 0:
                    time.sleep(0.4)
                    return _make_request(retry - 1)
                raise restkit.RequestFailed(str(e), http_code=0,
                        response=HTTPResponse({}))
            except restkit.RequestError, e: 
                # until py-restkit will be patched to only 
                # return RequestFailed, do our own raise
                raise restkit.RequestFailed(str(e), http_code=0,
                        response=HTTPResponse({}))
            except:
                raise
        try:
            data = _make_request()
        except restkit.RequestFailed, e:
            msg = getattr(e, 'msg', '')
            if msg and e.response.get('content-type') == 'application/json':
                
                try:
                    msg = anyjson.deserialize(msg)
                except ValueError:
                    pass
                    
            if type(msg) is dict:
                error = msg.get('reason')
            else:
                error = msg

            if e.status_code == 409:
                raise ResourceConflict(error[1], http_code=409,
                        response=e.response)
            elif e.status_code == 412:
                raise PreconditionFailed(error, http_code=412,
                        response=e.response)
            else:
                raise 
        except:
            raise
        response = self.get_response()
        
        if data and response.get('content-type') == 'application/json':
            try:
                data = anyjson.deserialize(data)
            except ValueError:
                pass
                
        return data

    def encode_params(self, params):
        """ encode parameters in json if needed """
        _params = {}
        if params:
            for name, value in params.items():
                if name in ('key', 'startkey', 'endkey') \
                        or not isinstance(value, basestring):
                    value = anyjson.serialize(value)
                _params[name] = value
        return _params
