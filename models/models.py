# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api
from ast import literal_eval
from datetime import datetime, timedelta
from openerp.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class FinancieraSucursal(models.Model):
	_inherit = 'financiera.entidad' 
	_name = 'financiera.entidad'

	type = fields.Selection([('sucursal', 'Sucursal'), ('comercio', 'Comercio')], string='Tipo', default='sucursal')
	father_id = fields.Many2one('financiera.entidad', 'Comercio padre')
	sucursal_id = fields.Many2one('financiera.entidad', 'Sucursal de dependencia')

class FinancieraPagoComercio(models.Model):
	_name = 'financiera.pago.comercio'

	name = fields.Char('Nombre')
	fecha = fields.Date('Fecha de pago')
	sucursal_id = fields.Many2one('financiera.entidad', 'Comercio', domain="[('type', '=', 'comercio')]")
	prestamo_ids = fields.One2many('financiera.prestamo', 'pago_comercio_id', 'Prestamos')
	pago_ids = fields.One2many('account.payment', 'pago_comercio_id', 'Pagos')
	monto = fields.Float('Monto total', digits=(16,2))
	state = fields.Selection([
		('borrador', 'Borrador'),
		('pagado', 'Pagado'),
		('cancelado', 'Cancelado')],
		string='Estado', readonly=True, default='borrador')
	company_id = fields.Many2one('res.company', 'Empresa', required=False, default=lambda self: self.env['res.company']._company_default_get('financiera.pago.comercio'))

	@api.model
	def create(self, values):
		rec = super(FinancieraPagoComercio, self).create(values)
		cr = self.env.cr
		uid = self.env.uid
		pago_comercio_ids = self.pool.get('financiera.pago.comercio').search(cr, uid, [('company_id', '=', rec.company_id.id)])
		_id = len(pago_comercio_ids)
		rec.update({
			'name': 'PAGO/'+str(rec.sucursal_id.id).zfill(4)+'/'+str(_id).zfill(8)
		})
		return rec

	@api.one
	def cancelar(self):
		for pago_id in self.pago_ids:
			pago_id.cancel()
		self.state = 'cancelado'

	@api.multi
	def wizard_confirmar_pago_comercio(self):
		currency_id = self.env.user.company_id.currency_id
		view_id = self.env['financiera.pago.comercio.confirmar.wizard']
		params = {
			'pago_comercio_id': self.id,
			'monto_pagado': self.monto,
			'currency_id': currency_id.id,
		}
		new = view_id.create(params)
		domain = []
		context = dict(self._context or {})
		current_uid = context.get('uid')
		current_user = self.env['res.users'].browse(current_uid)
		for journal_id in current_user.entidad_login_id.journal_disponibles_ids:
			if journal_id.type in ('cash', 'bank'):
				domain.append(journal_id.id)
		context = {'domain': domain}

		return {
			'type': 'ir.actions.act_window',
			'name': 'Confirmar Pago a comercio',
			'res_model': 'financiera.pago.comercio.confirmar.wizard',
			'view_type': 'form',
			'view_mode': 'form',
			'res_id': new.id,
			'view_id': self.env.ref('financiera_comercio.confirmar_pago_comercio_wizard', False).id,
			'target': 'new',
			'context': context,
		}

class ExtendsAccountPayment(models.Model):
	_inherit = 'account.payment'
	_name = 'account.payment'

	pago_comercio_id = fields.Many2one('financiera.pago.comercio', 'Pago a comercio')

class ExtendsFinancieraPrestamo(models.Model):
	_inherit = 'financiera.prestamo'
	_name = 'financiera.prestamo'

	pago_a_comercio = fields.Boolean('Pago a comercio')
	pago_a_comercio_fecha = fields.Date('Fecha de pago pactada')
	pago_comercio_id = fields.Many2one('financiera.pago.comercio', 'Contenedor de Pago a comercio')
	# Control time
	send_time = fields.Datetime('Hora de envio')
	send_minutes = fields.Float('Minutos en envio', compute='_compute_send_minutes')
	process_time = fields.Datetime('Hora de proceso')
	process_minutes = fields.Float('Minutos en proceso', compute='_compute_process_minutes')
	process_time_finish = fields.Datetime('Hora finalizacion de proceso')

	@api.model
	def default_get(self, fields):
		rec = super(ExtendsFinancieraPrestamo, self).default_get(fields)
		context = dict(self._context or {})
		current_uid = context.get('uid')
		current_user = self.env['res.users'].browse(current_uid)
		entidad_id = current_user.entidad_login_id
		if entidad_id.type == 'comercio':
			rec.update({
				'gestion_default_journal_id': entidad_id.journal_ajuste_invoice_id.id,
			})
		return rec

	@api.one
	def _compute_send_minutes(self):
		datetimeFormat = '%Y-%m-%d %H:%M:%S'
		date_start = None
		date_finish = datetime.now()
		if self.process_time:
			date_finish = datetime.strptime(self.process_time, datetimeFormat)
		if self.send_time:
			date_start = self.send_time
			start = datetime.strptime(date_start, datetimeFormat)
			finish = date_finish
			result = finish - start
			minutos = result.seconds / 60
			hours = (result.seconds) / 60
			self.send_minutes = minutos
		else:
			self.send_minutes = 0

	@api.one
	def _compute_process_minutes(self):
		datetimeFormat = '%Y-%m-%d %H:%M:%S'
		date_start = None
		date_finish = datetime.now()
		if self.process_time_finish:
			date_finish = datetime.strptime(self.process_time_finish,datetimeFormat)
		if self.process_time:
			date_start = self.process_time
			start = datetime.strptime(date_start, datetimeFormat)
			finish = date_finish
			result = finish - start
			minutos = result.seconds / 60
			self.process_minutes = minutos
		else:
			self.process_minutes = 0

	@api.model
	def notification_solicitudes(self):
		self.env.user.notify_warning('Hay Solicitudes en espera!')

	@api.one
	def send(self):
		self.notification_solicitudes()
		self.send_time = datetime.now()

	@api.one
	def processing(self):
		self.process_time = datetime.now()

	@api.one
	def open(self):
		self.process_time_finish = datetime.now()

	@api.one
	def cancel(self):
		self.process_time_finish = datetime.now()

	@api.one
	def calcular_cuotas_plan(self):
		rec = super(ExtendsFinancieraPrestamo, self).calcular_cuotas_plan()
		self.pago_a_comercio = self.plan_id.pago_a_comercio
		if self.plan_id.pago_a_comercio:
			self.pago_a_comercio_fecha = datetime.strptime(self.fecha, "%Y-%m-%d") + timedelta(days=self.plan_id.pago_a_comercio_dias)
		else:
			self.pago_a_comercio_fecha = False

class ExtendsFinancieraPrestamoPlan(models.Model):
	_inherit = 'financiera.prestamo.plan'
	_name = 'financiera.prestamo.plan'

	# Pago a Comercio
	pago_a_comercio = fields.Boolean('Pago a comercio')
	pago_a_comercio_dias = fields.Integer('Dias para la fecha de pago')

class ExtendsFinancieraPrestamoCuota(models.Model):
	_name = 'financiera.prestamo.cuota'
	_inherit = 'financiera.prestamo.cuota'

	comercio_id = fields.Many2one('financiera.entidad', 'Comercio')