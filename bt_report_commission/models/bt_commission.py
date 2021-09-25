# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError


class bt_commission(models.Model):
    _name = 'bt.commission'
    _description = 'Commissions'
    _rec_name = 'job'
    _order = 'job'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True,
                                 index=True, default=lambda self: self.env.company)
    job = fields.Many2one('bt.commission.job', string='job', required=True)
    profile = fields.Many2one('bt.commission.profile', string='profile', required=True)
    category = fields.Many2one('bt.commission.category', string='category', required=True)
    commission_percentage = fields.Float(string='Commission Percentage', required=True)
    active = fields.Boolean(default=True, string='active', required=True)