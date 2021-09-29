# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError


class bt_commission_job(models.Model):
    _name = 'bt.commission.job'
    _description = 'Jobs'
    _rec_name = 'name'
    _order = 'name'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True,
                                 index=True, default=lambda self: self.env.company)

    name = fields.Char(string='name', required=True)
    active = fields.Boolean(string='Active', default=True)

    profile_ids = fields.Many2many('bt.commission.profile', string='Profiles')

    def load_ids(self):
        for _self in self:
            if _self.id:
                ids = self.env["bt.commission"].search([('job','=',_self.id)])
                _self.profile_ids = ids.mapped('profile').ids

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if 'forced_load' in self._context:
            if self._context["forced_load"]:
                ids = self.env['bt.commission.job'].with_context(forced_load=False).search([])
                ids.load_ids()

        return super(bt_commission_job, self)._search(args, offset, limit, order, count, access_rights_uid)