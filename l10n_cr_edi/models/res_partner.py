import logging
import requests


from odoo import models, fields, api, _
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_cr_edi_vat_type = fields.Selection([
        ('01', 'Costarican citicen ID'),
        ('02', 'Legal entity'),
        ('03', 'DIMEX'),
        ('04', 'NITE'),
        ('XX', 'Foreigner')],
        string='ID type', help="ID type for CR eInvoicing.")
    # TODO onchange city en blanco en CR
    l10n_cr_edi_canton_id = fields.Many2one(
        'res.country.state.canton', ondelete='restrict')
    l10n_cr_edi_district_id = fields.Many2one(
        'res.country.state.canton.district', ondelete='restrict')
    l10n_cr_edi_neighborhood_id = fields.Many2one(
        'res.country.state.canton.district.neighborhood',
        ondelete='restrict')
    l10n_cr_edi_payment_method_id = fields.Many2one(
        'l10n_cr_edi.payment.method',
        string='eInvoice payment method',
        help="Indicates the way the invoice was/will be paid, where the options could be: "
        "Cash, Credit Card, Nominal Check etc. If unknown, please use cash.",
        default=lambda self: self.env.ref('l10n_cr_edi.payment_method_efectivo', raise_if_not_found=False))

    # -------------------------------------------------------------------------
    # ADDENDA
    # -------------------------------------------------------------------------
    l10n_cr_edi_addenda = fields.Many2one(
        comodel_name='ir.ui.view',
        string="Addenda",
        help="A view representing the addenda",
        domain=[('l10n_cr_edi_addenda_flag', '=', True)])

    @api.onchange('l10n_cr_edi_district_id')
    def _onchange_l10n_cr_edi_district_id(self):
        xml_district = self.l10n_cr_edi_district_id.get_external_id()
        if xml_district:
            xml_id = xml_district.get(self.l10n_cr_edi_district_id.id).split('.')[1]
            self.zip = ''.join(filter(str.isdigit, xml_id))

    @api.onchange('vat')
    def _onchange_vat(self):
        if self.vat:
            message, response = self.sugef_get(service="identificacion")
            if message:
                warning = {
                    'title': _("Warning for %s", self.vat),
                    'message': message
                }
                return {'warning': warning,
                        'value': {'name': False, 'l10n_cr_edi_vat_type': False}}
            self.name = response.get('nombre')
            self.l10n_cr_edi_vat_type = response.get('tipoIdentificacion')

    def sugef_get(self, service="", headers=False):

        url = "https://api.hacienda.go.cr/fe/ae"

        if not headers:
            headers = {"Content-Type": "application/json"}
        req = requests.get("%s?%s=%s" % (url, service, self.vat), headers)
        message, response = self.validate_response(req)
        return message, response

    def validate_response(self, req):
        """Validate the response obtained from treasury of Costa Rica.

        :param req: A class:`requests.models.Response` with request to HACIENDA
        :type req: class:`requests.models.Response`

        :return: A tuple with message and JSON dictionary with request from HACIENDA
        :rtype: tuple
        """
        message = ""
        if req.status_code == 401:
            return _("Unauthorized."), req
        if req.status_code == 500:
            message = _("Server Error.")
            return _("Server Error."), req
        if req.status_code in [404, 409]:
            return _("The ID number was not found in the Hacienda database. Please enter a valid number."), req

        if req.status_code in [200, 201]:
            return message, req.json()


class ResCountryStateCanton(models.Model):
    _description = "Canton"
    _name = 'res.country.state.canton'
    _order = 'code'

    state_id = fields.Many2one('res.country.state', string='State', required=True)
    name = fields.Char(
        string='Canton Name', required=True,
        help='Administrative divisions of a state. '
        'Used also for CR eInvoicing.')
    code = fields.Char(string='Canton Code',
                       help='The canton code.', required=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(state_id, code)',
         'The code of the canton must be unique by state!')
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args = args or []
        if self.env.context.get('country_id'):
            args = expression.AND([args, [
                ('state_id.country_id', '=', self.env.context.get('country_id'))]])

        if self.env.context.get('state_id'):
            args = args + [
                ('state_id', '=', self.env.context.get('state_id'))]

        if operator == 'ilike' and not (name or '').strip():
            first_domain = []
            domain = []
        else:
            first_domain = [('code', '=ilike', name)]
            domain = [('name', operator, name)]

        first_state_ids = self._search(expression.AND([first_domain, args]),
                                       limit=limit,
                                       access_rights_uid=name_get_uid) if first_domain else []
        return list(first_state_ids) + [state_id for state_id in self._search(
            expression.AND([domain, args]), limit=limit,
            access_rights_uid=name_get_uid) if state_id not in first_state_ids]


class ResCountryStateCantonDistrict(models.Model):
    _description = "District"
    _name = 'res.country.state.canton.district'
    _order = 'code'

    l10n_cr_edi_canton_id = fields.Many2one(
        'res.country.state.canton', string='Canton', required=True)
    name = fields.Char(string='District Name', required=True,
                       help='Administrative divisions of a Canton. '
                       'Used also for CR eInvoicing.')
    code = fields.Char(string='Discrict Code', help='The district code.',
                       required=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(l10n_cr_edi_canton_id, code)',
         'The code of the district must be unique by canton!')
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args = args or []
        if self.env.context.get('country_id'):
            args = expression.AND([args, [
                ('l10n_cr_edi_canton_id.state_id.country_id', '=', self.env.context.get('country_id'))]])

        if self.env.context.get('state_id'):
            args = args + [
                ('l10n_cr_edi_canton_id.state_id', '=', self.env.context.get('state_id'))]

        if self.env.context.get('l10n_cr_edi_canton_id'):
            args = args + [
                ('l10n_cr_edi_canton_id', '=',
                 self.env.context.get('l10n_cr_edi_canton_id'))]

        if operator == 'ilike' and not (name or '').strip():
            first_domain = []
            domain = []
        else:
            first_domain = [('code', '=ilike', name)]
            domain = [('name', operator, name)]

        first_state_ids = self._search(expression.AND([first_domain, args]),
                                       limit=limit,
                                       access_rights_uid=name_get_uid) if first_domain else []
        return list(first_state_ids) + [state_id for state_id in self._search(
            expression.AND([domain, args]), limit=limit,
            access_rights_uid=name_get_uid) if state_id not in first_state_ids]


class ResCountryStateCantonDistrictNeigh(models.Model):
    _description = "Neighborhood"
    _name = 'res.country.state.canton.district.neighborhood'
    _order = 'code'

    district_id = fields.Many2one('res.country.state.canton.district', string='District', required=True)
    name = fields.Char(string='Neighborhood Name', required=True,
                       help='Administrative divisions of a district. '
                       'Used also for CR eInvoicing.')
    code = fields.Char(string='Neighborhood Code',
                       help='The neighborhood code.', required=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(district_id, code)',
         'The code of the neighborhood must be unique by district!')
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args = args or []
        if self.env.context.get('country_id'):
            args = expression.AND([args, [
                ('district_id.l10n_cr_edi_canton_id.state_id.country_id', '=', self.env.context.get('country_id'))]])

        if self.env.context.get('state_id'):
            args = args + [('district_id.l10n_cr_edi_canton_id.state_id', '=',
                            self.env.context.get('state_id'))]
        if self.env.context.get('l10n_cr_edi_canton_id'):
            args = args + [('district_id.l10n_cr_edi_canton_id', '=',
                            self.env.context.get('l10n_cr_edi_canton_id'))]
        if self.env.context.get('district_id'):
            args = args + [('district_id', '=',
                            self.env.context.get('district_id'))]

        if operator == 'ilike' and not (name or '').strip():
            first_domain = []
            domain = []
        else:
            first_domain = [('code', '=ilike', name)]
            domain = [('name', operator, name)]

        first_state_ids = self._search(expression.AND([first_domain, args]),
                                       limit=limit,
                                       access_rights_uid=name_get_uid) if first_domain else []
        return list(first_state_ids) + [state_id for state_id in self._search(
            expression.AND([domain, args]), limit=limit,
            access_rights_uid=name_get_uid) if state_id not in first_state_ids]
