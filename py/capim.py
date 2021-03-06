#!/usr/bin/python
# -*- coding: utf8 -*-

import gzip
import calendar
import os
from email.utils import formatdate
from email.utils import parsedate

import ods

arquivos = {'index.html': {'content_type': 'text/html'},
            'capim.js': {'content_type': 'application/javascript'},
            'capim.css': {'content_type': 'text/css'},
            '20121.json': {'content_type': 'application/json'},
            '20122.json': {'content_type': 'application/json'},
            '20131.json': {'content_type': 'application/json'},
            '20132.json': {'content_type': 'application/json'},
            '20141.json': {'content_type': 'application/json'},
            }

DATA_PREFIX = '$BASE_PATH/data/'


# based on urlparse.py:parse_qs
def get_q(qs):
    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    for name_value in pairs:
        if not name_value:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            continue
        if nv[0] == 'q':
            return nv[1]
    raise IOError


def encoded_fname(environ):
    return get_q(environ['QUERY_STRING']).encode('hex') + '.json'


def run(environ, start_response):
    path = environ['PATH_INFO'][1:].split('/')
    use_gzip = False
    try:
        if 'gzip' in environ['HTTP_ACCEPT_ENCODING'].split(','):
            use_gzip = True
    except KeyError:
        pass

    path0 = path[0]
    if path0 == '' and environ['PATH_INFO'][0] == '/':
        path0 = 'index.html'

    if path0 in arquivos:
        arquivo = arquivos[path0]

        if 'uncompressed_length' not in arquivo:
            fname = path0
            with open(fname, 'rb') as fp:
                arquivo['uncompressed_data'] = fp.read()
            arquivo['uncompressed_length'] = str(os.path.getsize(fname))
            arquivo['last_modified_time'] = os.path.getmtime(fname)
            arquivo['last_modified_str'] = (
                formatdate(arquivo['last_modified_time'], False, True)
            )

        try:
            since_time = calendar.timegm(
                parsedate(environ['HTTP_IF_MODIFIED_SINCE'])
            )

            if arquivo['last_modified_time'] <= since_time:
                start_response('304 Not Modified', [])
                return ['']
        except KeyError:
            pass

        content_length = arquivo['uncompressed_length']
        content = arquivo['uncompressed_data']
        content_encoding = None

        if use_gzip:
            if 'compressed_length' not in arquivo:
                fname = path0 + '.gz'
                fp = open(fname, 'rb')
                arquivo['compressed_data'] = fp.read()
                fp.close()
                arquivo['compressed_length'] = str(os.path.getsize(fname))

            content_length = arquivo['compressed_length']
            content = arquivo['compressed_data']
            content_encoding = 'gzip'

        headers = [
            ('Content-Type', arquivo['content_type']),
            ('Last-Modified', arquivo['last_modified_str']),
            ('X-Uncompressed-Content-Length', arquivo['uncompressed_length']),
            ('Content-Length', content_length),
        ]

        if content_encoding is not None:
            headers.append(('Content-Encoding', content_encoding))

        start_response('200 OK', headers)
        return [content]

    elif path0 == 'load2.cgi':
        fname = encoded_fname(environ)
        data = None
        headers = [('Content-Type', 'application/json'), ('Expires', '-1')]
        try:
            # os arquivos estão em gzip. se gzip for pedido, o arquivo é
            # aberto normalmente e não é decodificado
            if use_gzip:
                fp = open(DATA_PREFIX + fname + '.gz', 'rb')
                headers.append(('Content-Encoding', 'gzip'))
            else:
                fp = gzip.open(DATA_PREFIX + fname + '.gz', 'rb')
            data = fp.read()
            fp.close()
        except IOError:
            pass
        if data is None:
            data = ''
        start_response('200 OK', headers)
        return [data]
    elif path0 == 'save2.cgi':
        fname = encoded_fname(environ)
        data = environ['wsgi.input'].read()
        with gzip.open(DATA_PREFIX + fname + '.gz', 'wb') as fp:
            fp.write(data)
        start_response(
            '200 OK',
            [('Content-Type', 'text/html'), ('Expires', '-1')]
        )
        return ['OK']
    elif path0 == 'ping.cgi':
        content_disposition = (
            f'attachment; filename={get_q(environ["QUERY_STRING"])}'
        )
        wsgi_input = environ['wsgi.input'].read().split('\r\n')
        terminator = wsgi_input[0] + '--'
        data = []
        started = False
        for line in wsgi_input[1:]:
            if line == terminator:
                break
            if started:
                data.append(line)
            if line == '':
                started = True
        data = '\r\n'.join(data)
        start_response(
            '200 OK',
            [('Content-Type', 'application/octet-stream'),
             ('Content-Disposition', content_disposition),
             ('Expires', '-1')]
        )
        return [data]
    elif path0 == 'ods.cgi':
        content_disposition = (
            f'attachment; filename={get_q(environ["QUERY_STRING"])}'
        )
        wsgi_input = environ['wsgi.input'].read().split('\r\n')
        terminator = wsgi_input[0] + '--'
        data = []
        started = False
        for line in wsgi_input[1:]:
            if line == terminator:
                break
            if started:
                data.append(line)
            if line == '':
                started = True
        data = '\r\n'.join(data)
        data = ods.run(data)
        start_response(
            '200 OK',
            [('Content-Type', 'application/octet-stream'),
             ('Content-Disposition', content_disposition),
             ('Expires', '-1')]
        )
        return [data]
    elif path0 == 'robots.txt':
        start_response('200 OK', [('Content-Type', 'text/plain')])
        data = "User-agent: *\nDisallow: /\n"
        return [data]

    raise IOError
