# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api
from ast import literal_eval
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class FinancieraSucursal(models.Model):
	_inherit = 'financiera.entidad' 
	_name = 'financiera.entidad'

	type = fields.Selection([('sucursal', 'Sucursal'), ('comercio', 'Comercio')], string='Tipo', default='sucursal')
	father_id = fields.Many2one('financiera.entidad', 'Comercio padre')
	sucursal_id = fields.Many2one('financiera.entidad', 'Sucursal de dependencia')

class ExtendsFinancieraPrestamo(models.Model):
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
		rec = super(ExtendsFinancieraPrestamo, self).default_get(fields)
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
		IrModelData = self.pool['ir.model.data']
		tree_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'financiera_prestamos.financiera_prestamo_tree')
		form_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'financiera_prestamos.financiera_prestamo_form')
		return {
			'domain': "[('id', 'in', ["+','.join(map(str, ids))+"])]",
			'name': ('Solicitudes'),
			'view_mode': 'tree,form',
			'res_model': 'financiera.prestamo',
			'views': [
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
            ],
			'type': 'ir.actions.act_window',
			'target': 'current',
		}

	# Esta funcion es reemplazada en caso de que este instalado
	# el modulo financiera_comercio
	@api.one
	def asignar_planes_disponibles(self):
		cr = self.env.cr
		uid = self.env.uid
		# self.actualizar_cupo()
		planes_obj = self.pool.get('financiera.prestamo.plan')
		planes_ids = planes_obj.search(cr, uid, [('state', '=', 'confirmado'),
			('es_refinanciacion', '=', self.es_refinanciacion)])

		self.delete_planes()
		for _id in planes_ids:
			plan_id = self.env['financiera.prestamo.plan'].browse(_id)
			if len(plan_id.prestamo_tipo_ids) == 0 or self.prestamo_tipo_id in plan_id.prestamo_tipo_ids:
				if len(plan_id.sucursal_ids) == 0 or self.sucursal_id in plan_id.sucursal_ids or self.comercio_id in plan_id.sucursal_ids:
					if len(plan_id.partner_tipo_ids) == 0 or self.partner_id.partner_tipo_id in plan_id.partner_tipo_ids:
						if (plan_id.recibo_de_sueldo == True and self.partner_id.recibo_de_sueldo == True) or (plan_id.recibo_de_sueldo == False):
							fpep_values = {
									'prestamo_id': self.id,
									'plan_id': plan_id.id,
							}
							fpep_id = self.env['financiera.prestamo.evaluacion.plan'].create(fpep_values)
							fpep_id.set_fecha_primer_vencimiento()
							self.plan_ids = [fpep_id.id]

class ExtendsFinancieraPrestamoCuota(models.Model):
	_inherit = 'financiera.prestamo.cuota'
	_name = 'financiera.prestamo.cuota'

	comercio_id = fields.Many2one('financiera.entidad', 'Comercio')

	@api.model
	def _actualizar_comercio_cuotas(self):
		cr = self.env.cr
		uid = self.env.uid
		cuotas_obj = self.pool.get('financiera.prestamo.cuota')
		cuotas_ids = cuotas_obj.search(cr, uid, [
				('comercio_id', '=', None)
			])
		_logger.info('Init Actualizar comercio en cuotas')
		count = 0
		for _id in cuotas_ids:
			cuota_id = cuotas_obj.browse(cr, uid, _id)
			cuota_id.comercio_id = cuota_id.prestamo_id.comercio_id.id
			count += 1
		_logger.info('Finish Actualizar comercio de cuotas: %s cuotas actualizadas', count)

	@api.model
	def default_get(self, fields):
		rec = super(ExtendsFinancieraPrestamoCuota, self).default_get(fields)
		rec.update({
			'sucursal_id': rec.prestamo_id.comercio_id.id,
		})


	def cuotas_de_comercio(self, cr, uid, ids, context=None):
		current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		domain = []
		entidad_id = current_user.entidad_login_id
		ids = []
		if entidad_id.type == 'comercio':
			ids = self.pool.get('financiera.prestamo.cuota').search(cr, uid, [('comercio_id', '=', entidad_id.id)])
		else:
			ids = self.pool.get('financiera.prestamo.cuota').search(cr, uid, [])
		IrModelData = self.pool['ir.model.data']
		tree_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'financiera_prestamos.financiera_prestamo_cuota_tree')
		form_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'financiera_prestamos.financiera_prestamo_cuota_form')
		return {
			'domain': "[('id', 'in', ["+','.join(map(str, ids))+"])]",
			'name': ('Cuotas del Comercio'),
			'view_mode': 'tree,form',
			'res_model': 'financiera.prestamo.cuota',
			'views': [
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
            ],
			'type': 'ir.actions.act_window',
			'target': 'current',
			'context': {'search_default_activa':1},
		}

	def reporte_graph_comercio_cuotas(self, cr, uid, ids, context=None):
		cuotas_obj = self.pool.get('financiera.prestamo.cuota')
		ids = cuotas_obj.search(cr, uid, [])
		for _id in ids:
			cuota_id = cuotas_obj.browse(cr, uid, _id)
			cuota_id.saldo_store = cuota_id.saldo
			cuota_id.cobrado_store = cuota_id.cobrado
			cuota_id.punitorio_store = cuota_id.punitorio
			cuota_id.total_store = cuota_id.total
		model_obj = self.pool.get('ir.model.data')
		data_id = model_obj._get_id(cr, uid, 'financiera_comercio', 'financiera_prestamo_cuota_comercio_graph')
		view_id = model_obj.browse(cr, uid, data_id, context=None).res_id
		
		return {
			'domain': "[('id', 'in', ["+','.join(map(str, ids))+"])]",
			'name': ('Grafico de cuotas segun comercio'),
			'view_mode': 'graph',
			'res_model': 'financiera.prestamo.cuota',
			'view_id': view_id,
			'type': 'ir.actions.act_window',
			'target': 'current',
			# 'context': {'search_default_a_facturar_mayor':1},
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
		IrModelData = self.pool['ir.model.data']
		kanban_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'base.res_partner_kanban_view')
		tree_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'base.view_partner_tree')
		form_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'base.view_partner_form')
		return {
			'domain': "[('id', 'in', ["+','.join(map(str, ids))+"])]",
			'name': ('Contactos'),
			'view_mode': 'kanban,tree,form',
			'res_model': 'res.partner',
			'views': [
                [kanban_view_id, 'kanban'],
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
            ],
			'type': 'ir.actions.act_window',
			'target': 'current',
		}