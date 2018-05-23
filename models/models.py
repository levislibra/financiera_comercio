# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api
from ast import literal_eval
from datetime import datetime, timedelta
# import pyglet
# import pygame

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
	asigned_id = fields.Many2one('res.users', 'Asignado a')
	current_user_id = fields.Many2one('res.users', 'Usuario actual', compute='_compute_current_user')
	is_change_asigned = fields.Boolean(compute='_compute_is_change_asigned')
	note = fields.Text('Nota')
	state = fields.Selection([('draft', 'Borrador'), ('send', 'Enviado'), ('processing', 'Procesando'), ('open', 'Abierta'), ('confirm', 'Confirmada'), ('cancel', 'Cancelada')], string='Estado', readonly=True, default='draft')
	# Prestamo
	prestamo_id = fields.Many2one('financiera.prestamo', 'Prestamo')
	plan_ids = fields.One2many('financiera.prestamo.partner.plan', 'prestamo_id', 'Planes', related='prestamo_id.plan_ids')
	cuota_ids = fields.One2many('financiera.prestamo.cuota', 'prestamo_id', 'Cuotas', related='prestamo_id.cuota_ids')
	default_iva = fields.Boolean("IVA", related='prestamo_id.iva')
	vat_tax_id = fields.Many2one('account.tax', 'Tasa de IVA', domain="[('type_tax_use', '=', 'sale')]", related='prestamo_id.vat_tax_id')

	@api.model
	def create(self, values):
		rec = super(FinancieraSolicitud, self).create(values)
		configuracion_id = self.env['financiera.configuracion'].browse(1)
		rec.update({
			'name': 'SOL-' + str(rec.id).zfill(6),
			'iva': configuracion_id.default_iva,
			'vat_tax_id': configuracion_id.vat_tax_id.id			
			})
		return rec

	@api.multi
	def wizard_seleccionar_plan(self):
		self.prestamo_id.asignar_planes_disponibles()
		params = {
			'prestamo_id': self.prestamo_id.id,
		}
		view_id = self.env['financiera.prestamo.wizard']
		new = view_id.create(params)
		return {
			'type': 'ir.actions.act_window',
			'name': 'Seleccionar Plan',
			'res_model': 'financiera.prestamo.wizard',
			'view_type': 'form',
			'view_mode': 'form',
			'res_id': new.id,
			'view_id': self.env.ref('financiera_prestamos.prestamo_seleccionar_plan_wizard', False).id,
			'target': 'new',
		}


	@api.one
	def _compute_current_user(self):
		self.current_user_id = self.env.user

	@api.one
	def _compute_is_change_asigned(self):
		self.is_change_asigned = self.current_user_id.id == self.asigned_id.id

	@api.one
	def send(self):
		self.state = 'send'
		self.notification_solicitudes()
		fp_values = {
				'cliente_id': self.partner_id.id,
				'monto_otorgado': self.amount,
				'responsable_id': self.partner_id.responsable_id.id
		}
		fp_id = self.env['financiera.prestamo'].create(fp_values)
		self.prestamo_id = fp_id.id

	@api.model
	def notification_solicitudes(self):
		self.env.user.notify_warning('Hay Solicitudes en espera!')
		# myfile = '/opt/odoo/custom-addons/libra-addons/financiera_comercio/static/description/alert.wav'
		# sound = pyglet.media.load(myfile)
		# core = pyglet.media.Player()
		# core.queue(sound)
		# core.play()
		# values = {
		# 	'status': 'draft',
		# 	'title': u'Be notified about',
		# 	'message': "Do not forget to send notification in 21.04.17",
		# 	'partner_ids': [(6, 0, [1, 5])]
		# }
		# self.env['popup.notification'].create(values)


	@api.one
	def draft(self):
		self.state = 'draft'
		self.prestamo_id.unlink()

	@api.one
	def processing(self):
		self.state = 'processing'
		self.asigned_id = self.env.user

	@api.one
	def open(self):
		self.state = 'open'

	@api.one
	def confirm(self):
		self.state = 'confirm'

	@api.one
	def cancel(self):
		self.state = 'cancel'

	# def report_detalle_prestamo(self, cr, uid, ids, context=None):
	# 	if context is None:
	# 		context = {}
	# 	data = {}
	# 	data['ids'] = context.get('active_ids', [])
	# 	data['model'] = context.get('active_model', 'ir.ui.menu')
	# 	return self.pool['report'].get_action(cr, uid, [], 'financiera_comercio.detalle_prestamo', data=data, context=context)