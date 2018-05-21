# -*- coding: utf-8 -*-
from openerp import http

# class FinancieraComercio(http.Controller):
#     @http.route('/financiera_comercio/financiera_comercio/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/financiera_comercio/financiera_comercio/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('financiera_comercio.listing', {
#             'root': '/financiera_comercio/financiera_comercio',
#             'objects': http.request.env['financiera_comercio.financiera_comercio'].search([]),
#         })

#     @http.route('/financiera_comercio/financiera_comercio/objects/<model("financiera_comercio.financiera_comercio"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('financiera_comercio.object', {
#             'object': obj
#         })