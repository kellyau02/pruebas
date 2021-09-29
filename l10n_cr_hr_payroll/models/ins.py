# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import division

import calendar
import logging
from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class L10crIns(models.AbstractModel):
    _name = "l10n_cr.ins"
    _inherit = "account.report"
    _description = "INS"

    filter_date = {'mode': 'range', 'date_from': '', 'date_to': '', 'filter': 'this_month'}
    filter_all_entries = None

    def _get_columns_name(self, options):
        return [
            {},
            {'name': _('Identification Card')},
            {'name': _('Insurance')},
            {'name': _('Name')},
            {'name': _('Last Name')},
            {'name': _('S. Last Name')},
            {'name': _('Birth Day')},
            {'name': _('Phone Number'), 'class': 'number'},
            {'name': _('Email')},
            {'name': _('Gender')},
            {'name': _('Marital Status')},
            {'name': _('Nationality')},
            {'name': _('Total'), 'class': 'number'},
            {'name': _('Workday')},
            {'name': _('Job Position')},
        ]

    def get_working_date(self, employee):
        """Based on employee category, verify if a category set in this
        employee come from this module and get code."""
        category = employee.category_ids.filtered(lambda r: r.color == 3)
        if not category or not category[0].get_external_id()[
                category[0].id].startswith('l10n_cr_hr_payroll'):
            return ''
        return category[0].name[:2]

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        context = self._set_context(options)
        slips = self.env['hr.payslip'].search([
            ('date_from', '>=', context['date_from']), ('date_to', '<=', context['date_to'])])
        marital_status = {'single': 1, 'married': 2, 'widower': 3, 'divorced': 4}
        for employee in slips.mapped('employee_id'):
            name = employee.name.split(' ')
            amount = round(sum(slips.filtered(lambda sl: sl.employee_id == employee).mapped('line_ids').filtered(
                lambda line: line.code == 'BRUTO').mapped('amount')), 2)
            columns = [
                (employee.identification_id or '').zfill(10),
                (employee.identification_id or '').zfill(10),
                ' '.join(name[0:-2]),
                name[-2],
                name[-1],
                fields.datetime.strftime(employee.birthday, '%d/%m/%Y') if employee.birthday else '',
                employee.mobile_phone,
                employee.work_email,
                [dict(employee._fields['gender'].selection).get(employee.gender), {
                    'male': '1', 'female': '2'}.get(employee.gender, ' ') or ' '],
                [dict(employee._fields['marital'].selection).get(employee.marital) or 'NA',
                 marital_status.get(employee.marital) or '9'],
                employee.country_id.code,
                amount,
                self.get_working_date(employee),
                [employee.job_id.name, employee.job_id.code],
            ]
            lines.append({
                'id': str(employee.id),
                'name': '',
                'columns': [{'name': v[0] if isinstance(v, list) else v,
                             'value': v[1] if isinstance(v, list) else ''} for index, v in enumerate(columns)],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
        return lines

    @api.model
    def _get_report_name(self):
        return _('INS')

    def _get_reports_buttons(self):
        buttons = super()._get_reports_buttons()
        buttons += [{'name': _('TXT'), 'action': 'print_txt'}]
        return buttons

    def get_txt(self, options):
        ctx = self._set_context(options)
        ctx.update({'no_format': True, 'print_mode': True, 'raise': True})
        return self.with_context(ctx)._l10n_cr_ins_txt_export(options)

    def _l10n_cr_ins_txt_export(self, options):
        txt_data = self._get_lines(options)
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        date = fields.datetime.strptime(
            self.env.context['date_from'], DEFAULT_SERVER_DATE_FORMAT)
        lines = '%sM%s%s %s%s%s %s\nEmail %s' % (
            company.l10n_cr_ins_number or '',
            date.year,
            str(date.month).zfill(2),
            (company.company_registry or '').ljust(20, ' '),
            (company.phone or '').replace('-', '').replace(' ', ''),
            (company.l10n_cr_ins_fax or '').replace('-', '').replace(' ', ''),
            company.l10n_cr_ins_header or '', company.l10n_cr_ins_email or '')
        lines += '\nDomicilio %s, %s\n' % ((company.street or '').upper(), (company.street2 or '').upper())
        for line in txt_data:
            columns = line.get('columns', [])
            data = [''] * 20
            data[0] = columns[0]['name'].ljust(20, ' ')
            data[1] = columns[1]['name'].ljust(20, ' ')
            data[2] = columns[2]['name'][:15].ljust(15, ' ').upper()
            data[3] = columns[3]['name'][:15].ljust(15, ' ').upper()
            data[4] = columns[4]['name'][:15].ljust(15, ' ').upper()
            data[5] = columns[5]['name'] or '          '
            data[6] = (columns[6]['name'] or '').replace(' ', '').ljust(8, ' ')
            data[7] = (columns[7]['name'] or '')[:40].ljust(40, ' ')
            data[8] = columns[8]['value']
            data[9] = columns[9]['value']
            data[10] = columns[10]['name'] or '  '
            data[11] = ('%.2f' % (columns[11]['name'] or 0)).zfill(13)
            data[12] = '0'
            data[13] = calendar.monthrange(date.year, date.month)[1]
            data[14] = '024'
            data[15] = columns[12]['name'] or '00'
            data[16] = '100'
            data[17] = (columns[13]['value'] or '').ljust(4, ' ')
            lines += ''.join(str(d) for d in data) + '\n'
        return lines
