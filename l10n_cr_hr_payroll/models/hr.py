from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    code = fields.Char(help='Code defined for this job.')
