
# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError

from datetime import datetime

class bt_rpt_cmn_account_line_calculator(models.Model):
    _name = 'bt.rpt.cmn.account.line.calculator'
    _description = 'Report - Account Line - Calculator'
    _rec_name = 'id'
    _order = "id"

    account_line_id = fields.Many2one('account.move.line', string='Account', required=True,
                    ondelete="cascade")

    collaborator = fields.Many2one('res.users', string='collaborator')
    job
# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError

from datetime import datetime

class bt_rpt_cmn_account_line_calculator(models.Model):
    _name = 'bt.rpt.cmn.account.line.calculator'
    _description = 'Report - Account Line - Calculator'
    _rec_name = 'id'
    _order = "id"

    account_line_id = fields.Many2one('account.move.line', string='Account', required=True,
                    ondelete="cascade")

    collaborator = fields.Many2one('res.users', string='collaborator')
    job = fields.Many2one('bt.commission.job', string='job')
    profile = fields.Many2one('bt.commission.profile', string='profile')
    category = fields.Many2one('bt.commission.category', string='category')

    commission_percentage = fields.Float(string='Commission Percentage')
    amount_commission = fields.Float(string='Commision Amount', default=0)
    # id = fields.Integer(string='id', readonly=True) , required=True


    utility_sale = fields.Float(string='Utility Sale')#,   # currency_field="company_currency_id")
    utility_percentage = fields.Float(string='Utility Percentage')

    amount_payment = fields.Float(string='Payment Amount', default=0)
    percentage_payment = fields.Float(string='Payment Percentage', default=0)
    total_payment = fields.Float(string='Full Payment', default=0)
    
    commission_payment = fields.Float(string='Payment Commission', default=0)
    # _get_reconciled_invoices_partials

    def run_payment(self):
        

        # if 'type' in self._context:
        #     if self._context["type"] == 'payments':
        type_change = (self.account_line_id.credit + self.account_line_id.debit) / self.account_line_id.price_subtotal
        payments = self.account_line_id.move_id._get_reconciled_invoices_partials()
        self.amount_payment = sum([x[1] 
            if x[2].payment_id.date >= fields.Date.to_date(self._context.get('date_start')) and 
               x[2].payment_id.date <= fields.Date.to_date(self._context.get('date_finish')) else 0 for x in payments]) * type_change #[2].payment_id.date
        self.percentage_payment = (self.account_line_id.price_total / self.account_line_id.move_id.amount_total) * 100
        self.total_payment = self.amount_payment * (self.percentage_payment / 100)
        self.commission_payment = self.total_payment / (1 + ((self.account_line_id.price_total - self.account_line_id.price_subtotal) / self.account_line_id.price_subtotal))




        