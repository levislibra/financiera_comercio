# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api
from ast import literal_eval
from datetime import datetime, timedelta

class FinancieraSucursal(models.Model):
	_inherit = 'financiera.entidad' 
	_name = 'financiera.entidad'

	type = fields.Selection([('sucursal', 'Sucursal'), ('comercio', 'Comercio')], string='Tipo', default='sucursal')


class FinancieraSolicitud(models.Model):
	_name = 'financiera.solicitud'

	name = fields.Char('Nro de solicitud', readonly=True)
	partner_id = fields.Many2one('res.partner', 'Cliente')
	comercio_id = fields.Many2one('financiera.entidad', 'Comercio')
	amount = fields.Monetary('Monto')
	currency_id = fields.Many2one('res.currency', 'Moneda')
	note = fields.Text('Nota')
	state = fields.Selection([('draft', 'Borrador'), ('send', 'Enviado'), ('processing', 'Procesando'), ('open', 'Abierta'), ('confirm', 'Confirmada'), ('cancel', 'Cancelada')], string='Estado', readonly=True, default='draft')

	@api.model
	def create(self, values):
		rec = super(FinancieraSolicitud, self).create(values)
		rec.update({
			'name': 'SOL-' + str(rec.id).zfill(6),
			})
		return rec

	@api.one
	def send(self):
		self.state = 'send'

	@api.one
	def draft(self):
		self.state = 'draft'

	@api.one
	def processing(self):
		self.state = 'processing'

	@api.one
	def open(self):
		self.state = 'open'

	@api.one
	def confirm(self):
		self.state = 'confirm'

	@api.one
	def cancel(self):
		self.state = 'cancel'
