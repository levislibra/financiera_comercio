# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api
from ast import literal_eval
from datetime import datetime, timedelta

class FinancieraSucursal(models.Model):
	_inherit = 'financiera.entidad' 
	_name = 'financiera.entidad'

	type = fields.Selection([('sucursal', 'Sucursal'), ('comercio', 'Comercio')], string='Tipo', default='sucursal')
	father_id = fields.Many2one('financiera.entidad', 'Comercio padre')
	sucursal_id = fields.Many2one('financiera.entidad', 'Sucursal de dependencia')

class FinancieraPrestamo(models.Model):
	_inherit = 'financiera.prestamo'
	_name = 'financiera.prestamo'

	comercio_id = fields.Many2one('financiera.entidad', 'Comercio')
	asigned_id = fields.Many2one('res.users', 'Asignado a')
	# Control time
	send_time = fields.Datetime('Hora de envio')
	send_minutes = fields.Float('Minutos en envio', compute='_compute_send_minutes')
	process_time = fields.Datetime('Hora de proceso')
	process_minutes = fields.Float('Minutos en proceso', compute='_compute_process_minutes')
	process_time_finish = fields.Datetime('Hora finalizacion de proceso')

	@api.model
	def default_get(self, fields):
		rec = super(FinancieraPrestamo, self).default_get(fields)
		context = dict(self._context or {})
		current_uid = context.get('uid')
		current_user = self.env['res.users'].browse(current_uid)
		entidad_id = current_user.entidad_login_id
		if entidad_id.type == 'comercio':
			rec.update({
				'sucursal_id': entidad_id.sucursal_id.id,
				'comercio_id': entidad_id.id,
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


	def iniciativas_de_comercio(self, cr, uid, ids, context=None):
		current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		domain = []
		entidad_id = current_user.entidad_login_id
		ids = []
		if entidad_id.type == 'comercio':
			ids = self.pool.get('financiera.prestamo').search(cr, uid, [('comercio_id', '=', entidad_id.id)])
		else:
			ids = self.pool.get('financiera.prestamo').search(cr, uid, [])
		model_obj = self.pool.get('ir.model.data')
		data_id = model_obj._get_id(cr, uid, 'financiera_prestamos', 'financiera_prestamo_tree')
		view_id = model_obj.browse(cr, uid, data_id, context=None).res_id
		view_form_id = model_obj.get_object_reference(cr, uid, 'financiera_prestamos', 'financiera_prestamo_tree')
		return {
			'domain': "[('id', 'in', ["+','.join(map(str, ids))+"])]",
			'name': ('Solicitudes'),
			'view_mode': 'tree,form',
			'res_model': 'financiera.prestamo',
			'view_ids': [view_id, view_form_id[1]],
			'type': 'ir.actions.act_window',
			'target': 'current',
		}

class ExtendsResPartner(models.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'

	comercio_id = fields.Many2one('financiera.entidad', "Comercio")
	is_user_login_comercio = fields.Boolean('Usuario actual esta logueado en comercio', compute='_compute_is_user_login_comercio')
	
	@api.model
	def create(self, values):
		rec = super(ExtendsResPartner, self).create(values)
		context = dict(self._context or {})
		current_uid = context.get('uid')
		current_user = self.env['res.users'].browse(current_uid)
		comercio_id = current_user.entidad_login_id.id or False
		rec.update({
			'comercio_id': comercio_id,
		})
		return rec

	@api.one
	def _compute_is_user_login_comercio(self):
		cr = self.env.cr
		uid = self.env.uid
		current_user = self.pool.get('res.users').browse(cr, uid, uid, context=None)
		self.is_user_login_comercio = current_user.entidad_login_id.type == 'comercio'

	def comercio_contacts_action(self, cr, uid, ids, context=None):
		current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		domain = []
		entidad_id = current_user.entidad_login_id
		ids = []
		if entidad_id.type == 'comercio':
			ids = self.pool.get('res.partner').search(cr, uid, [('comercio_id', '=', entidad_id.id)])
		else:
			ids = self.pool.get('res.partner').search(cr, uid, [])
		model_obj = self.pool.get('ir.model.data')
		data_id = model_obj._get_id(cr, uid, 'base', 'res_partner_kanban_view')
		view_id = model_obj.browse(cr, uid, data_id, context=None).res_id
		view_form_id = model_obj.get_object_reference(cr, uid, 'base', 'res_partner_kanban_view')
		return {
			'domain': "[('id', 'in', ["+','.join(map(str, ids))+"])]",
			'name': ('Contactos'),
			'view_mode': 'kanban,tree,form',
			'res_model': 'res.partner',
			'view_ids': [view_id, view_form_id[1]],
			'type': 'ir.actions.act_window',
			'target': 'current',
		}