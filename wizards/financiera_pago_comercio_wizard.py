# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import time

class FinancieraPagoComercioWizard(models.TransientModel):
	_name = 'financiera.pago.comercio.wizard'

	@api.multi
	def confirmar(self):
		context = dict(self._context or {})
		active_ids = context.get('active_ids')

		monto = 0
		sucursal_id = None
		comercio_old_id = None
		if len(active_ids) > 0:
			for _id in active_ids:
				prestamo_id = self.env['financiera.prestamo'].browse(_id)
				sucursal_id = prestamo_id.sucursal_id.id
				if comercio_old_id != None and comercio_old_id != sucursal_id:
					raise ValidationError("Todos los prestamos deben ser del mismo comercio.")
				comercio_old_id = sucursal_id
				monto += prestamo_id.saldo_a_pagar

			fpc_values = {
				'fecha': datetime.now(),
				'sucursal_id': sucursal_id,
				'prestamo_ids': [(6,0,active_ids)],
				'monto': monto,
			}
			fpc_id = self.env['financiera.pago.comercio'].create(fpc_values)

			action = self.env.ref('financiera_comercio.financiera_pago_comercio_action')
			result = action.read()[0]
			form_view = self.env.ref('financiera_comercio.financiera_pago_comercio_form')
			result['views'] = [(form_view.id, 'form')]
			result['res_id'] = fpc_id.id
			return result

class FinancieraPagoComercioConfirmarWizard(models.TransientModel):
	_name = 'financiera.pago.comercio.confirmar.wizard'

	pago_comercio_id = fields.Many2one('financiera.pago.comercio', 'Liquidacion a comercio')
	prestamo_id = fields.Many2one('financiera.prestamo', 'Prestamo')
	payment_date = fields.Date('Fecha de pago', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
	payment_communication = fields.Char('Circular', default='Pago por cuenta y orden del cliente')
	journal_id = fields.Many2one('account.journal', 'Metodo de Pago', domain="[('type', 'in', ('bank', 'cash'))]")
	monto_pagado = fields.Float('Efectivo a comercio')
	currency_id = fields.Many2one('res.currency', "Moneda")

	@api.one
	def confirmar_pago_comercio(self):
		for prestamo_id in self.pago_comercio_id.prestamo_ids:
			len_pagos_antes = len(prestamo_id.payment_ids)
			prestamo_id.confirmar_pagar_prestamo(self.payment_date, prestamo_id.saldo_a_pagar, self.journal_id, self.payment_communication)
			len_pagos_despues = len(prestamo_id.payment_ids)
			if len_pagos_despues != (1 + len_pagos_antes):
				raise ValidationError("Pago no generado del prestamo "+str(prestamo_id.name))
			self.pago_comercio_id.pago_ids = [prestamo_id.payment_last_id.id]
		self.pago_comercio_id.state = 'pagado'
		self.pago_comercio_id.fecha = self.payment_date