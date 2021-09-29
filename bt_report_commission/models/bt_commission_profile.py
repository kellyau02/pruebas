# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError


class bt_commission_profile(models.Model):
    _name = 'bt.commission.profile'
    _description = 'Profiles'
    _rec_name = 'name'
    _order = 'name'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True,
                                 index=True, default=lambda self: self.env.company)

    name = fields.Char(string='name', required=True)
    active = fields.Boolean(string='Active', default=True)
