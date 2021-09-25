# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
import json
from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError


class bt_commission_wizard(models.TransientModel):
    _name = 'bt.commission.wizard'
    _description = 'Commission Wizard'
    _rec_name = 'collaborator'
    _order = 'job'

    profile = fields.Many2one('bt.commission.profile', string='profile', required=True)
    job = fields.Many2one('bt.commission.job', string='job', required=True)
    # job_id_domain = fields.Char(compute="_compute_job_id_domain", readonly=True, store=False)
    category = fields.Many2one('bt.commission.category', string='category')

    collaborator = fields.Many2one('res.users', string='collaborator', required=True)
    type = fields.Selection([('sales', 'Sales'),
                             ('payments', 'Payments')], default='payments',
                            string='type', required=True)

    date_start = fields.Date(string='Date start', required=True)
    date_finish = fields.Date(string='Date finish', required=True)


    @api.onchange('profile')
    def _onchange_profile(self):
        self.job = False
        self.category = False

    @api.onchange('job')
    def _onchange_job(self):
        self.category = False

    @api.depends('profile')
    def _compute_job_id_domain(self):
        for rec in self:
            rec.job_id_domain = json.dumps([('profile', '=', rec.profile.id)])

    # @api.onchange('profile')
    # def onchange_profile(self):
    #     for rec in self:
    #         return {'domain': {'job': [('profile','=', rec.profile.id)]}}

    def generate_commission_profile(self):
        res = self.env["ir.actions.act_window"]._for_xml_id('bt_report_commission.action_bt_account_line_report')
        res['target'] = 'main' # self new current        
        # res['domain'] = [('order_sale_id','=',self.id)]
        domains = [('parent_state','!=','draft')]
        domains.append(('category','!=',False)) # not in
        context = dict(self._context)
        context['date_start'] = self.date_start
        context['date_finish'] = self.date_finish
        if self.category:
            domains.append(('category','=',self.category.id))
        if self.type == 'payments':
            domains.append(('amount_payment','>',0))            
        else:
            domains.append(('date','>=',self.date_start))
            domains.append(('date','<=',self.date_finish))

        res['domain'] = domains
        # if self.category:
        #     domain.append(('category','=',self.category.id))
        # if self.category:
        #     domain.append(('category','=',self.category.id))

        
        context["run_commission"] = True #'amount_commission':5.5
        context["job"] = self.job.id if self.job else False
        context["profile"] = self.profile.id if self.profile else False
        context["category"] = self.category.id if self.category else False
        context["collaborator"] = self.collaborator.id if self.collaborator else False
        context["type"] = self.type if self.type else False
        res['context'] = context
        return res

    @api.model
    def default_get(self, field_list):
        resp = super().default_get(field_list)
        return resp

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        resp = super()._read_group_stage_ids(stages, domain, order)
        return resp

    # @api.model
    # def get_job