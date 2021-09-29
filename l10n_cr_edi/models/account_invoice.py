import base64
import json
import logging
import random
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pytz
import requests
from requests.exceptions import RequestException
from lxml.objectify import fromstring

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = 'account.move'

    def _get_default_l10n_cr_edi_economic_activity(self):
        company = self.company_id or self.env.company
        if company.l10n_cr_edi_economic_activity_ids:
            return company.l10n_cr_edi_economic_activity_ids[0].id
        return False

    def domain_economic_activity(self):
        if self._context.get('default_move_type', '') in ('in_invoice', 'in_refund'):
            return []
        return [('id', 'in', self.env.company.l10n_cr_edi_economic_activity_ids.ids)]

    # ==== EDI flow fields ====
    l10n_cr_edi_cfdi_request = fields.Selection(
        selection=[
            ('on_invoice', "On Invoice"),
            ('on_refund', "On Credit Note"),
        ],
        string="Request a EDI", store=True,
        compute='_compute_l10n_cr_edi_cfdi_request',
        help="Flag indicating a EDI should be generated for this journal entry.")
    l10n_cr_edi_sat_status = fields.Selection(
        selection=[
            ('none', 'State not defined'),
            ('signed', 'Not Synced Yet'),
            ('not_signed', 'Waiting for answer'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected')],
        help='Refers to the status of the invoice inside the SAT system.',
        readonly=True,
        copy=False,
        required=True,
        tracking=True,
        default='none')

    l10n_cr_edi_emission_datetime = fields.Datetime(
        string='Emission date & time',
        help='Refers to the date and time of emission of '
        'the invoice inside the DGT system.',
        copy=False)
    l10n_cr_edi_attempts = fields.Integer(
        string='Number of attempts',
        help="Number of Attempts",
        default=0,
        copy=False)
    l10n_cr_edi_security_code = fields.Char(
        string="Security_code",
        help="Security_code",
        size=8,
        copy=False)
    l10n_cr_edi_return_code = fields.Char(
        string="Return code",
        help="Return code",
        copy=False)
    l10n_cr_edi_return_message = fields.Char(
        string="Explanatory message of the state",
        help="Explanatory message of the state")
    l10n_cr_edi_bool = fields.Boolean(
        string='Is eInvoice?',
        help='Is eInvoice?',
        compute='_compute_l10n_cr_edi_bool',
        copy=False)
    l10n_cr_edi_type = fields.Selection([
        ('01', 'Electronic invoice'),
        ('02', 'Electronic debit note'),
        ('03', 'Electronic credit note'),
        ('04', 'Electronic ticket'),
        ('08', 'Electronic purchase invoice'),
        ('09', 'Electronic invoice for export')],
        string='eInvoice document type',
        help='eInvoice document type',
        copy=False)
    l10n_cr_edi_state_treas = fields.Selection(
        selection=[
            ('1', 'Accepted'),
            ('2', 'Parcially accepted'),
            ('3', 'Rejected')
        ],
        string='Treasury acknowledgment',
        help='Treasury acknowledgment',
        copy=False)
    l10n_cr_edi_state_customer = fields.Selection(
        selection=[
            ('1', 'Accepted'),
            ('2', 'Parcially accepted'),
            ('3', 'Rejected')
        ],
        string='Customer acknowledgment',
        help='Customer acknowledgment',
        copy=False)
    l10n_cr_edi_xml_filename = fields.Char(
        string='eInvoice XML Filename',
        help='eInvoice XML Filename',
        copy=False)
    l10n_cr_edi_xml_binary = fields.Binary(
        string='eInvoice XML',
        help='eInvoice XML',
        copy=False)
    l10n_cr_edi_pdf_filename = fields.Char(
        string='eInvoice PDF Filename',
        help='eInvoice PDF Filename',
        copy=False)
    l10n_cr_edi_pdf_binary = fields.Binary(
        string='eInvoice PDF',
        help='eInvoice PDF',
        copy=False)
    l10n_cr_edi_xml_customer_filename = fields.Char(
        string='eInvoice Customer ack. Filename',
        help='eInvoice Customer ack. Filename',
        copy=False)
    l10n_cr_edi_xml_customer_binary = fields.Binary(
        string='eInvoice Customer ack. XML',
        help='eInvoice Customer ack. XML',
        copy=False)
    l10n_cr_edi_consecutive_number_receiver = fields.Char(
        string='consecutive_number_receiver',
        help='consecutive_number_receiver',
        copy=False)
    l10n_cr_edi_full_number = fields.Char(
        string='eInvoice Full Number',
        help='eInvoice Full Number',
        copy=False)
    l10n_cr_edi_ref_type = fields.Selection(
        selection=[
            ('01', 'Anula documento electrónico'),
            ('02', 'Corrige monto'),
            ('04', 'Referencia a otro documento'),
            ('05', 'Sustituye comprobante provisional de contingencia'),
            ('99', 'Otro tipo de referencia')],
        string='eInvoice reference type',
        copy=False,
        help="Select if this document refers to another document.")
    # TODO contraint doc if ref_id
    l10n_cr_edi_ref_doc = fields.Selection(
        selection=[
            ('01', 'Electronic document'),
            ('02', 'Electronic debit note'),
            ('03', 'Electronic credit note'),
            ('04', 'Electronic ticket'),
            ('05', 'Dispatch note'),
            ('06', 'Contrato'),
            ('07', 'Procedure'),
            ('08', 'Electronic invoice issued in contingency'),
            ('09', 'Return merchandise'),
            ('10', 'Replaces Electronic invoice rejected by DGT'),
            ('11', 'Replaces the rejected Electronic invoice by the Receiver'),
            ('12', 'Replaces Electronic Export Invoice'),
            ('13', 'eInvoice month expired'),
            ('14', 'Electronic Invoice provided by taxpayer of the Simplified Tax Regime'),
            ('15', 'Replace an Electronic Purchase Invoice'),
            ('99', 'Other type of document')],
        string='eInvoice reference document type',
        copy=False,
        help="Select the reference document type.")
    l10n_cr_edi_ref_num = fields.Char(
        string='eInvoice reference document number',
        help='eInvoice reference document number',
        copy=False)
    l10n_cr_edi_ref_reason = fields.Char(
        string='eInvoice reference Reason',
        help='eInvoice reference Reason',
        copy=False)
    l10n_cr_edi_reference_datetime = fields.Datetime(
        string='eInvoice reference date and time of issue',
        help='eInvoice reference date and time of issue',
        copy=False)
    l10n_cr_edi_ref_id = fields.Many2one(
        'account.move',
        string='eInvoice reference document',
        help='eInvoice reference document',
        copy=False)
    l10n_cr_edi_economic_activity_id = fields.Many2one(
        'l10n.cr.account.invoice.economic.activity',
        string="Economic Activity",
        help="Economic Activity",
        default=_get_default_l10n_cr_edi_economic_activity,
        domain=lambda self: self.domain_economic_activity())
    #   FIXME load information from company_id
    l10n_cr_edi_purchase_export_einvoice = fields.Boolean(
        string="Purchase or Export einvoice",
        help="Purchase or Export einvoice",
        default="False")

    l10n_cr_edi_tax_exemption_id = fields.Many2one(
        'l10n_cr_edi.tax.exemption',
        'Tax Exemption',
        help="Indicates the exemption general for the invoice. "
        "If several exonerations are required, please use the exemption field in each invoice line.",)

    l10n_cr_edi_payment_method_id = fields.Many2one(
        'l10n_cr_edi.payment.method',
        string='Payment method',
        help="Indicates the way the invoice was/will be paid, where the options could be: "
        "Cash, Credit Card, Nominal Check etc. If unknown, please use cash.",
        default=lambda self: self.env.ref('l10n_cr_edi.payment_method_efectivo', raise_if_not_found=False))

    l10n_cr_edi_presentation_position = fields.Selection(
        selection=[
            ('1', 'Normal'),
            ('2', 'Contingencia'),
            ('3', 'Sin Internet')
        ],
        string='eInvoice presentation position',
        help='eInvoice presentation position',
        default='1')

    l10n_cr_edi_sale_condition = fields.Selection(
        selection=[
            ('01', 'Cash'),
            ('02', 'Credit'),
            ('03', 'Consignment'),
            ('04', 'Set aside'),
            ('05', 'Lease with purchase option'),
            ('06', 'Lease in financial function'),
            ('07', 'Payment to a third party'),
            ('08', 'Services provided to the State on credit'),
            ('09', 'Service payments provided to the State'),
            ('99', 'Others')
        ],
        string='eInvoice sale conditions',
        help='eInvoice sale conditions',
        default='01')

    l10n_cr_edi_rel_document_type = fields.Selection(
        string='Journal document type',
        help='Journal document type',
        related='journal_id.l10n_cr_edi_document_type',
        store=False,
        readonly=True)
    l10n_cr_currency_rate = fields.Float(
        string="Currency rate for invoicing in CR",
        help="Currency rate for invoicing in CR")

    # -------------------------------------------------------------------------
    # ADDENDA
    # -------------------------------------------------------------------------
    l10n_cr_edi_addenda = fields.Many2one(
        related='partner_id.l10n_cr_edi_addenda', string="Addenda assigned to partner")

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """Use payment method from partner or set Cash as default"""
        res = super(AccountInvoice, self)._onchange_partner_id()
        self.l10n_cr_edi_payment_method_id = (
            self.partner_id.l10n_cr_edi_payment_method_id or self.env.ref(
                'l10n_cr_edi.payment_method_efectivo', raise_if_not_found=False))
        return res

    @api.onchange('l10n_cr_edi_payment_method_id')
    def _onchange_l10n_cr_edi_payment_method_id(self):
        """Trigger method when Payment method is Debit or Credit Card according Article 39 of the DGT Regulation
        establishes that the service provider must reimburse the tax charged to the final consumer, when they
        use the any Card Payment Method."""
        if self.l10n_cr_edi_payment_method_id.fiscal_position_id:
            for line in self.invoice_line_ids.filtered(lambda l: l.product_id.type == 'service'):
                line._set_price_and_tax_after_fpos()
            self._move_autocomplete_invoice_lines_values()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id', 'state')
    def _compute_l10n_cr_edi_cfdi_request(self):
        edi_format = self.env.ref('l10n_cr_edi.edi_fedgt_4_3', False)
        for move in self:
            if not edi_format or move.country_code != 'CR' or edi_format not in move.journal_id.edi_format_ids:
                move.l10n_cr_edi_cfdi_request = False
            elif move.move_type in ['out_invoice', 'in_invoice']:
                move.l10n_cr_edi_cfdi_request = 'on_invoice'
            elif move.move_type == ['out_refund', 'in_refund']:
                move.l10n_cr_edi_cfdi_request = 'on_refund'
            else:
                move.l10n_cr_edi_cfdi_request = False

    @api.depends('journal_id', 'journal_id.l10n_cr_edi_document_type')
    def _compute_l10n_cr_edi_bool(self):
        for invoice in self:
            invoice.l10n_cr_edi_bool = bool(
                invoice.journal_id.l10n_cr_edi_document_type)

    def _reverse_moves(self, default_values_list, cancel=False):
        """When is created the invoice refund is assigned all the l10n_cr_edi reference information to generate
        the credit note"""
        for i, move in enumerate(self):
            if move.move_type == 'out_invoice' and move.journal_id.l10n_cr_edi_document_type:
                default_values_list[i].update({
                    'l10n_cr_edi_ref_type': '02' if move.l10n_cr_edi_type else '04',
                    'l10n_cr_edi_ref_doc': '01' if move.l10n_cr_edi_type else '99',
                    'l10n_cr_edi_ref_num': move.name if move.l10n_cr_edi_type else '',
                    'l10n_cr_edi_ref_id': move.id if move.l10n_cr_edi_type else False,
                    'l10n_cr_edi_ref_reason': default_values_list[i]['ref'] or _('Refund'),
                    'l10n_cr_edi_reference_datetime': move.l10n_cr_edi_emission_datetime,
                    'l10n_cr_edi_economic_activity_id': move.l10n_cr_edi_economic_activity_id.id,
                    'l10n_cr_edi_security_code': '{:08}'.format(random.randrange(1, 10 ** 8))
                })
        return super(AccountInvoice, self)._reverse_moves(default_values_list, cancel=cancel)

    @api.onchange('l10n_cr_edi_ref_type')
    def _onchange_ref_type_values(self):
        self.l10n_cr_edi_ref_doc = False
        if not self.l10n_cr_edi_ref_type:
            self.l10n_cr_edi_ref_num = False
            self.l10n_cr_edi_ref_id = False
        if self.l10n_cr_edi_ref_type != '05':
            self.invoice_date = False

    def l10n_cr_edi_amount_to_text(self):
        """Method to transform a float amount to text words
        E.g. 100.10 - One Hundread with 10/100 (Colons)
        :returns: Amount transformed to words costarican format for invoices
        :rtype: str
        """
        self.ensure_one()
        # Split integer and decimal part
        amount_i, amount_d = divmod(self.amount_total, 1)
        amount_d = round(amount_d, 2)
        amount_d = int(round(amount_d * 100, 2))
        with_ = _('with')
        currency_label = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').currency_unit_label
        if self.currency_id == self.env.ref('base.CRC'):
            currency_label = _('Colons')
        words = self.currency_id.with_context(
            lang=self.partner_id.lang or 'es_ES').amount_to_text(amount_i).rsplit(' ', 1)[0]
        invoice_words = '%(words)s %(with_)s %(amount_d)02d/100 (%(currency_label)s)' % dict(
            words=words, with_=with_, amount_d=amount_d, currency_label=currency_label)
        return invoice_words

    def validate_cyberfuel_base(self):
        #   TODO Add logic to validate cyberfuel information
        return True

    def get_cyberfuel_doc_type(self):
        if self.move_type in ['out_refund', 'in_refund']:
            return '03'
        if not self.journal_id.l10n_cr_edi_document_type:
            raise ValidationError(_('The eInvoicing document type is required. Please check your journal settings.'))
        return self.journal_id.l10n_cr_edi_document_type

    def get_taxes(self, line, subtotal):
        dict_tax = []
        iva_returned = 0.0
        for tax in line.tax_ids.filtered(
                lambda x: x.l10n_cr_edi_code):
            tax_line = {}
            tax_line.update({
                'codigo': tax.l10n_cr_edi_code
            })
            if tax.l10n_cr_edi_code in ('01', '07'):
                tax_line.update({
                    'codigotarifa': tax.l10n_cr_edi_iva_code
                })

            monto = round(subtotal * tax.amount / 100, 5)
            tax_line.update({
                'tarifa': tax.amount,
                'monto': monto
            })

            if tax.l10n_cr_edi_code in ('07', '08'):
                tax_line.update({
                    'factoriva': round(tax.amount / 100, 5)
                })

            if tax.tax_group_id.id == self.env.ref('l10n_cr_edi.tax_group_iva_4_returned').id:
                monto = round(subtotal * tax.l10n_cr_edi_original_amount / 100, 5)
                tax_line.update({
                    'tarifa': tax.l10n_cr_edi_original_amount,
                    'monto': monto
                })
                iva_returned = monto

            if tax.l10n_cr_edi_exempt:
                exempt = {}

                monto = round(subtotal * tax.l10n_cr_edi_original_amount / 100, 5)

                tax_line.update({
                    'tarifa': tax.l10n_cr_edi_original_amount,
                    'monto': monto
                })
                percentage = tax.amount
                if tax.l10n_cr_edi_original_amount:
                    percentage = tax.l10n_cr_edi_original_amount - tax.amount

                exemption = line.l10n_cr_edi_tax_exemption_id or self.l10n_cr_edi_tax_exemption_id
                exempt.update({
                    'tipodocumento': exemption.exempt_type,
                    'numerodocumento': exemption.name,
                    'nombreinstitucion': exemption.issuer,
                    'fechaemision': datetime.strftime(
                        exemption.exempt_date, "%Y-%m-%dT%H:%M:%S-06:00") if exemption else '',
                    'porcentajeexoneracion': percentage,
                    'montoexoneracion':
                        round(subtotal * (tax.l10n_cr_edi_original_amount - tax.amount) / 100, 5)
                })

                tax_line.update({
                    'exoneracion': exempt
                })
            # FIXME include node exportacion

            dict_tax.append(tax_line)
        return dict_tax, iva_returned

    def get_invoice_key(self):
        key = {}
        location = 1
        if self.env.context.get('force_location'):
            location = self.env.context.get('force_location')
        elif self.journal_id.l10n_cr_edi_location:
            location = self.journal_id.l10n_cr_edi_location
        terminal = 1
        if self.env.context.get('force_terminal'):
            terminal = self.env.context.get('force_terminal')
        elif self.journal_id.l10n_cr_edi_terminal:
            terminal = self.journal_id.l10n_cr_edi_terminal

        location = str(location).zfill(3)
        terminal = str(terminal).zfill(5)
        key.update({
            'sucursal': location,
            'terminal': terminal,
            'tipo': self.get_cyberfuel_doc_type(),
            'comprobante': str(self.sequence_number).zfill(10),
            'pais': self.company_id.country_id.phone_code or '506',
            'dia': datetime.strftime(self.l10n_cr_edi_emission_datetime, "%d"),
            'mes': datetime.strftime(self.l10n_cr_edi_emission_datetime, "%m"),
            'anno': datetime.strftime(self.l10n_cr_edi_emission_datetime, "%y"),
            'situacion_presentacion': (
                self.l10n_cr_edi_presentation_position or str(1)),
            'codigo_seguridad': self.l10n_cr_edi_security_code
        })
        return key

    def datetime_requested_format(self):
        now_utc = datetime.now(pytz.timezone('UTC'))
        now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
        self.l10n_cr_edi_emission_datetime = now_cr.strftime("%Y-%m-%d %H:%M:%S")
        date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
        return date_cr

    def get_invoice_header(self):
        header = {}
        header.update({
            'codigo_actividad': self.l10n_cr_edi_economic_activity_id.code,
            'fecha': self.datetime_requested_format(),
            'condicion_venta': self.l10n_cr_edi_sale_condition or '01',
            'plazo_credito': self.invoice_payment_term_id.line_ids.days or '0',
            'medio_pago': self.l10n_cr_edi_payment_method_id.code,
        })

        return header

    def get_partner_address(self, partner_id):
        address = {}
        check = (partner_id.country_id.code == 'CR' and
                 (partner_id.state_id or partner_id.l10n_cr_edi_canton_id or
                  partner_id.l10n_cr_edi_district_id or
                  partner_id.l10n_cr_edi_neighborhood_id or
                  partner_id.street))
        if check:
            address = {
                'provincia': partner_id.state_id.l10n_cr_edi_code,
                'canton': partner_id.l10n_cr_edi_canton_id.code,
                'distrito': partner_id.l10n_cr_edi_district_id.code,
                'barrio': partner_id.l10n_cr_edi_neighborhood_id.code
            }
            if partner_id.street:
                address.update({
                    'sennas': "%s\n%s" % (
                        partner_id.street or '', partner_id.street2 or '')
                })
        else:
            return "%s%s%s%s%s" % (
                partner_id.country_id.name or '',
                partner_id.state_id.name or '', partner_id.city or '',
                partner_id.street or '', partner_id.street2 or '')

        return address

    def get_issuing_company_info(self):
        company = {}
        company.update({
            'nombre': self.company_id.name,
            'identificacion': {
                'tipo': self.company_id.l10n_cr_edi_vat_type,
                'numero': self.company_id.vat,
            }
        })

        if self.company_id.l10n_cr_edi_tradename:
            company.update({
                'nombre_comercial': self.company_id.l10n_cr_edi_tradename,
            })
        company.update({
            'ubicacion': self.get_partner_address(self.company_id.partner_id),
        })

        # TODO use mobile if not phone
        if self.company_id.phone:
            phone_information = {}
            phone_information.update({
                'numero': self.company_id.phone.replace(' ', ''),
                'cod_pais': self.company_id.country_id.phone_code,
            })
            company.update({
                'telefono': phone_information
            })
        #   TODO    Add fax information

        if self.company_id.email:
            company.update({
                'correo_electronico': self.company_id.email
            })
        return company

    #   FIXME   Try to unify it with get_issuing_company_info
    def get_partner_info(self):
        partner = {'nombre': self.partner_id.name}

        if self.partner_id.l10n_cr_edi_vat_type in ['01', '02', '03', '04']:
            if self.partner_id.vat:
                partner.update({
                    'identificacion': {
                        'tipo': self.partner_id.l10n_cr_edi_vat_type,
                        'numero': self.partner_id.vat,
                    }
                })

            partner.update({
                'ubicacion': self.get_partner_address(self.partner_id),
            })
        elif self.partner_id.l10n_cr_edi_vat_type == 'XX':
            if self.partner_id.vat:
                ubicacion = self.get_partner_address(self.partner_id)
                partner.update({
                    'IdentificacionExtranjero': self.partner_id.vat,
                    'sennas_extranjero': ubicacion
                })

        phone = self.partner_id.phone or self.partner_id.mobile
        if phone:
            phone_information = {}
            phone_information.update({
                'numero': phone.replace(' ', ''),
                'cod_pais': self.partner_id.country_id.phone_code,
            })
            partner.update({
                'telefono': phone_information
            })
        #   TODO    Add fax information

        if self.partner_id.email:
            partner.update({
                'correo_electronico': self.partner_id.email
            })
        return partner

    def l10n_cr_edi_is_required(self):
        self.ensure_one()
        return self.company_id.country_id == self.env.ref('base.cr')

    def l10n_cr_edi_log_error(self, message, attachment_ids=None):
        self.ensure_one()
        self.message_post(body=_('Error during the process: %s') % message,
                          attachment_ids=attachment_ids)

    def get_reference_information(self):
        date = self.l10n_cr_edi_reference_datetime
        inv = False
        if self.l10n_cr_edi_ref_doc == '01':
            if self.l10n_cr_edi_ref_id:
                inv = self.l10n_cr_edi_ref_id
            else:
                inv = self.search(
                    [('name', '=', self.l10n_cr_edi_ref_num)])
        if inv and inv.id != self.id and inv.l10n_cr_edi_emission_datetime:
            date = inv.l10n_cr_edi_emission_datetime
        reference = {
            'tipo_documento': self.l10n_cr_edi_ref_doc,
            'numero_documento':
                inv and inv.l10n_cr_edi_full_number or
                self.l10n_cr_edi_ref_num,
            'fecha_emision': date and date.strftime(
                "%Y-%m-%dT%H:%M:%S-06:00") or False,
            'codigo': self.l10n_cr_edi_ref_type,
            'razon': self.l10n_cr_edi_ref_reason
        }
        if (inv and self.l10n_cr_edi_ref_type in
                ['01', '02'] and inv.amount_total == self.amount_total):
            # Full refund
            reference['codigo'] = '01'
        elif inv and self.l10n_cr_edi_ref_type in ['01', '02']:
            # Fix amount
            reference['codigo'] = '02'
            # TODO: Must be a list of references
        return [reference]

    @api.model
    def l10n_cr_edi_xml_customer_binary_to_str(self, xml=None):
        """Get an objectified tree representing the xml.
        If the xml is not specified, retrieve it from the attachment.

        :param xml: The xml as string
        :return: An objectified tree
        """
        # TODO helper which is not of too much help and should be removed
        self.ensure_one()
        if xml is None and self.l10n_cr_edi_xml_customer_binary:
            xml = base64.decodebytes(self.l10n_cr_edi_xml_customer_binary)
        return fromstring(xml) if xml else None

    def _get_exchange_rate(self):
        currency_cr = self.env.ref('base.CRC')
        if self.currency_id == currency_cr:
            return 1
        date = self._context.get('date') or fields.Date.today()
        return round(self.currency_id._convert(1, currency_cr, self.company_id, date), 5)

    def action_post(self):
        """It's Required Support from edi documents for in_invoice
        In CR there is an Electronic invoice for purchases. This is an Electronic document issued by the purchaser
        of a good or service to support the operation carried out, in this document the provider who sells the
        service is not obliged to issue electronic documents.
        Then this invoice must be issued by the buyers and sent to DGT.
        """
        result = super().action_post()
        edi_document_vals_list = []
        for move in self.filtered(lambda m: m.country_code == 'CR' and m.move_type in ['in_invoice', 'in_refund']):
            edi_format = self.env.ref('l10n_cr_edi.edi_fedgt_4_3')
            existing_edi_document = move.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)

            if edi_format._is_required_for_invoice(move):
                if existing_edi_document:
                    existing_edi_document.write({
                        'state': 'to_send',
                        'error': False,
                        'blocking_level': False,
                    })
                else:
                    edi_document_vals_list.append({
                        'edi_format_id': edi_format.id,
                        'move_id': move.id,
                        'state': 'to_send',
                    })

        return result

    def _post(self, soft=True):
        # OVERRIDE
        for move in self:
            if move.l10n_cr_edi_cfdi_request not in ('on_invoice', 'on_refund'):
                continue

            lines = move.invoice_line_ids.filtered('price_unit')
            invalid_uom_products = lines.product_id.filtered(lambda product: not product.l10n_cr_edi_uom_id)
            if invalid_uom_products:
                raise UserError(_("You need to define an 'UoM eInvoicing' on the following products: %s") % ', '.join(
                    invalid_uom_products.mapped('display_name')))
            invalid_cabys_products = lines.product_id.filtered(
                lambda product: not product.l10n_cr_edi_code_cabys_id and
                product.categ_id != self.env.ref('l10n_cr_edi.product_category_other_charges'))
            if invalid_cabys_products:
                raise UserError(_("You need to define an 'CABYS code' on the following products: %s") % ', '.join(
                    invalid_cabys_products.mapped('display_name')))
            invalid_code_taxes = lines.tax_ids.filtered(lambda tax: not tax.l10n_cr_edi_code)
            if invalid_code_taxes:
                raise UserError(_("You need to define an 'eInvoicing code' on the following taxes: %s") % ', '.join(
                    invalid_code_taxes.mapped('name')))
            if not move.l10n_cr_edi_economic_activity_id:
                raise UserError(_("You need to define an 'Economic activity' on the invoice."))

            move.l10n_cr_edi_security_code = '{:08}'.format(random.randrange(1, 10 ** 8))
            if move.currency_id:
                move.l10n_cr_currency_rate = move._get_exchange_rate()

        return super()._post(soft=soft)

    def l10n_cr_edi_document_request(self):
        if self.l10n_cr_edi_is_required():
            self.electronic_document_request()

    def l10n_cr_edi_answer_request(self):
        if self.l10n_cr_edi_is_required():
            self.electronic_answer_request()

    @api.model
    def _cron_l10n_cr_edi_answer_request(self, limit=10, number_of_days=3):
        last_day = fields.Datetime.now() - relativedelta(days=number_of_days)
        to_request = self.search([
            ('date', '>=', last_day),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('edi_state', '=', 'sent'),
            ('l10n_cr_edi_sat_status', 'in', ['signed', 'not_signed'])
        ], limit=limit)
        for i in to_request:
            try:
                i.l10n_cr_edi_answer_request()
            except Exception as e:
                i.l10n_cr_edi_log_error(str(e))

    def _action_server_update_emission_datetime(self):
        self.ensure_one()
        if self.l10n_cr_edi_is_required():
            try:
                xml = base64.decodebytes(
                    self.l10n_cr_edi_xml_binary)
                root = fromstring(xml)

                if hasattr(root, 'FechaEmision'):
                    date = root['FechaEmision']
                    date = datetime.strptime(
                        str(date), "%Y-%m-%dT%H:%M:%S-06:00")
                    self.l10n_cr_edi_emission_datetime = date

                _logger.info('Emission datetime updated correctly')
            except Exception as e:
                self.l10n_cr_edi_log_error(str(e))

    def _asssign_message_error_to_einvoice(self, data):
        self.ensure_one()
        if not data or not self.l10n_cr_edi_is_required():
            return False
        try:
            xml = base64.decodebytes(data.encode())
            root = fromstring(xml)

            if hasattr(root, 'DetalleMensaje'):
                message = root['DetalleMensaje']
                message = re.findall(r'\[(.*)\]', message.pyval, re.MULTILINE | re.DOTALL)
                if not message:
                    return False

                message = message[0].split('\n')

                result = []
                for line in message:
                    match = re.findall(r'"(.*)"', line, re.MULTILINE | re.DOTALL)

                    if not match:
                        continue

                    result.append(match[0])

                if result:
                    self.l10n_cr_edi_return_message = '\n'.join(result)

            _logger.info('Return message updated correctly')
        except Exception as e:
            self.l10n_cr_edi_log_error(str(e))
        return True

    def _l10n_cr_edi_generate_document_name(self):
        document_types = {
            '01': _('FE-%s.xml'),
            '02': _('ND-%s.xml'),
            '04': _('TE-%s.xml'),
            '08': _('FEC-%s.xml'),
            '09': _('FEE-%s.xml')
        }
        if self.move_type == 'out_refund':
            return _('NC-%s.xml') % self.name
        if self.journal_id.l10n_cr_edi_document_type in document_types:
            return document_types[
                self.journal_id.l10n_cr_edi_document_type] % self.name
        return False

    #   Validate if the client is linked to a company.
    #   If so, the email will be on behalf of the company
    def _get_partner_to_email(self):
        if self.partner_id.commercial_partner_id:
            partner_id = self.partner_id.commercial_partner_id
        else:
            partner_id = self.partner_id
        return partner_id

    # Send electronic invoice email to the customer
    def l10n_cr_edi_send_mail(self):
        self.env.ref('account.email_template_edi_invoice').send_mail(self.id, force_send=True,)

    def l10n_cr_edi_get_environment_id(self):
        self.ensure_one()
        if self.company_id.l10n_cr_edi_test_env:
            return 'c3RhZw=='
        return 'cHJvZA=='

    def l10n_cr_edi_call_service(self, service, headers, data):
        mode = 'stag' if self.company_id.l10n_cr_edi_test_env else 'prod'
        url = "https://www.comprobanteselectronicoscr.com/api/%s.%s.43" % (service, mode)
        response = False
        try:
            response = requests.post(url, headers=headers, data=data)
        except Exception as e:
            self.l10n_cr_edi_log_error(str(e))
        return response

    #   This method allows from a numeric key to obtain the XML
    #   information signed in base64
    def electronic_document_request(self):
        try:
            payload = {
                'api_key': self.company_id.l10n_cr_edi_client_api_key,
                'clave': self.l10n_cr_edi_full_number,
            }
            response_document = self.l10n_cr_edi_call_service('consultadocumento', {}, json.dumps(payload))
            if not response_document:
                return
            response_content = json.loads(response_document._content)

            if response_content.get('code') != '1':
                error_message = "%s: %s<br/>%s" % (
                    response_content.get('code'),
                    response_content.get('xml_error', ''),
                    response_content.get('data'))
                self.l10n_cr_edi_log_error(error_message)
                return

            self.write({
                'l10n_cr_edi_xml_filename': self._l10n_cr_edi_generate_document_name(),
                'l10n_cr_edi_xml_binary': response_content.get('xml'),
            })
        except Exception as e:
            _logger.info(e)

    #   This method allows from a numeric key to obtain the XML
    #   information signed in base64
    def electronic_answer_request(self):
        payload = {
            'api_key': self.company_id.l10n_cr_edi_client_api_key,
            'clave': self.l10n_cr_edi_full_number,
        }
        try:
            response_document = self.l10n_cr_edi_call_service('consultahacienda', {}, json.dumps(payload))
        except RequestException as error:
            _logger.warning('Connection error with PAC during %s Request', error)
            return False

        if not response_document:
            return False
        response_content = json.loads(response_document._content)
        self.l10n_cr_edi_return_code = response_content.get('code')
        if 'xml_error' in response_content:
            self.l10n_cr_edi_log_error("%s: %s<br/>%s" % (
                response_content.get('code'),
                response_content.get('xml_error', ''),
                response_content.get('data', '')))

        answer = response_content.get('hacienda_result', {}).get('ind-estado')
        if not answer:
            self.l10n_cr_edi_log_error("%s: %s" % (
                response_content.get('code'),
                response_content.get('data'),
            ))
            return False

        if answer == 'error':
            error_message = str(response_content.get('hacienda_result', {}).get('ind-estado'))
            self.l10n_cr_edi_log_error(error_message)
            return False

        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': _('AHC-%s.xml') % self.name,
            'res_id': self.id,
            'res_model': self._name,
            'type': 'binary',
            'datas': response_content.get('hacienda_result', {}).get('respuesta-xml'),
            'mimetype': 'application/xml',
            'description': _('Electronic message confirmation generated for the %s document.') % self.name,
        })
        # == Chatter ==
        self.message_post(
            body=_("The XML for message confirmation was successfully received from the government."),
            attachment_ids=attachment_id.ids,
        )
        if answer == 'rechazado':
            self.l10n_cr_edi_sat_status = 'rejected'
            self._asssign_message_error_to_einvoice(response_content.get('hacienda_result', {}).get('respuesta-xml'))
            return False
        self.write({
            'l10n_cr_edi_sat_status': 'accepted',
        })
        self.l10n_cr_edi_send_mail()
        return True

    def _define_tax_condition(self):
        taxes = self.invoice_line_ids.tax_ids
        if taxes.filtered(lambda r:
                          r.l10n_cr_edi_tax_condition == '05'):
            return '05'  # Proporcionalidad
        if taxes.filtered(lambda r:
                          r.l10n_cr_edi_tax_condition == '03'):
            return '03'  # Bienes de capital

        if taxes.filtered(lambda r:
                          r.l10n_cr_edi_tax_condition == '04'):
            if taxes.filtered(lambda r:
                              r.l10n_cr_edi_tax_condition == '01'):
                return '02'  # Genera crédito parcial del IVA
            return '04'
        return '01'

    def _get_einvoicing_tax_information(self, root):
        result = {}

        if type != "07":
            result.update({
                'tax_condition': self._define_tax_condition(),
            })

        tax_to_be_credited = float()
        if hasattr(root, 'ResumenFactura'):
            tax_to_be_credited = root['ResumenFactura']['TotalImpuesto'].pyval

        result.update({
            'tax_to_be_credited': tax_to_be_credited,
            'tax_to_be_expensed': self.amount_tax - tax_to_be_credited
        })
        return result

    #   This method allows the customer send the answer (partial, complete
    #    or reject the electronic invoice) as as an Electronic Receiver
    #    before the DGT.
    def send_xml(self):
        self.ensure_one()
        if not self.l10n_cr_edi_is_required():
            return
        if not self.l10n_cr_edi_xml_customer_binary:
            return
        root = self.l10n_cr_edi_xml_customer_binary_to_str()
        if not self.l10n_cr_edi_state_customer:
            raise ValidationError(_('Notification!.\n You must select the type of response for the loaded file.'))

        self.l10n_cr_edi_security_code = '{:08}'.format(random.randrange(1, 10 ** 8))
        if (self.company_id.l10n_cr_edi_client_api_key and
                self.l10n_cr_edi_state_customer):
            if self.l10n_cr_edi_state_customer == '1':
                detalle_mensaje = 'Aceptado'
                doc_type = "05"
                code = "EIA"
            if self.l10n_cr_edi_state_customer == '2':
                detalle_mensaje = 'Aceptado parcial'
                doc_type = "06"
                code = "EIPA"
            if self.l10n_cr_edi_state_customer == '3':
                detalle_mensaje = 'Rechazado'
                doc_type = "07"
                code = "EIR"
            if hasattr(root, 'ResumenFactura'):
                monto_total_impuesto = \
                    root['ResumenFactura']['TotalImpuesto'].pyval
            else:
                monto_total_impuesto = ''

            if not self.l10n_cr_edi_consecutive_number_receiver:
                seq = self.env['ir.sequence'].search([
                    ('code', '=', code),
                    ('company_id', '=', self.company_id.id)])
                self.l10n_cr_edi_consecutive_number_receiver = seq.next_by_id()

            # Crea el consecutivo de la FE
            if (not self.journal_id.l10n_cr_edi_location or not
                    self.journal_id.l10n_cr_edi_terminal):
                raise UserError(_(
                    'Notification!.\nPlease configure the purchase '
                    'journal, add terminal and location.'))

            result = self._get_einvoicing_tax_information(root)
            tax_to_be_credited = result['tax_to_be_credited']
            tax_to_be_expensed = result['tax_to_be_expensed']
            tax_condition = result['tax_condition']
            clave = {
                'tipo': doc_type,
                'sucursal': str(self.journal_id.l10n_cr_edi_location).zfill(3),
                'terminal': str(self.journal_id.l10n_cr_edi_terminal).zfill(5),
                'numero_documento': root['Clave'].text,
                'numero_cedula_emisor':
                    root['Emisor']['Identificacion']['Numero'].text,
                'fecha_emision_doc': root['FechaEmision'].text,
                'mensaje': self.l10n_cr_edi_state_customer,
                'detalle_mensaje': detalle_mensaje,
                'codigo_actividad': self.l10n_cr_edi_economic_activity_id.code,
                'condicion_impuesto': tax_condition,
                'impuesto_acreditar': tax_to_be_credited,
                'gasto_aplicable': tax_to_be_expensed,
                'monto_total_impuesto': monto_total_impuesto,
                'total_factura':
                    root['ResumenFactura']['TotalComprobante'].pyval,
                'numero_cedula_receptor': self.company_id.vat,
                'num_consecutivo_receptor':
                    self.l10n_cr_edi_consecutive_number_receiver,
                'codigo_seguridad': self.l10n_cr_edi_security_code,
                'dia': datetime.strftime(self.invoice_date, "%d"),
                'mes': datetime.strftime(self.invoice_date, "%m"),
                'anno': datetime.strftime(self.invoice_date, "%y"),
            }

            if tax_condition != '05':
                clave.update({
                    'codigo_actividad':
                        self.l10n_cr_edi_economic_activity_id.code
                })

            payload = {
                'api_key': self.company_id.l10n_cr_edi_client_api_key,
                'clave': clave,
                'emisor': {
                    'identificacion': {
                        'tipo': root['Emisor']['Identificacion']['Tipo'].text,
                        'numero':
                        root['Emisor']['Identificacion']['Numero'].text
                    }
                },
                "parametros": {
                    "enviodgt": "A"
                }
            }
            response_document = self.l10n_cr_edi_call_service('acceptbounce', {}, json.dumps(payload))
            if not response_document:
                return
            response_content = json.loads(response_document._content)

            if not response_content.get('code'):
                self.l10n_cr_edi_sat_status = 'rejected'
                _logger.info('Error trying to send answer. %s', response_document._content)
                return

            if response_content.get('code') in [1, 43, 44]:
                self.write({
                    'l10n_cr_edi_xml_filename': 'ARC-%s.xml' % self.l10n_cr_edi_consecutive_number_receiver,
                    'l10n_cr_edi_xml_binary': response_content.get('data'),
                    'l10n_cr_edi_sat_status': 'accepted',
                    'l10n_cr_edi_full_number': response_content.get('clave')
                })
                self.l10n_cr_edi_answer_request()
                # TODO Send email notifying about answer


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_cr_edi_tax_exemption_id = fields.Many2one(
        'l10n_cr_edi.tax.exemption', 'Tax Exemption',
        help="Indicates the exemption for this line if is different to the general in the invoice.")

    def _set_price_and_tax_after_fpos(self):
        """Trigger method to include fiscal Position for l10n_cr_edi Payment methods."""
        res = super()._set_price_and_tax_after_fpos()
        for line in self.filtered(lambda l: l.tax_ids and l.move_id.l10n_cr_edi_payment_method_id.fiscal_position_id):
            line.tax_ids = line.move_id.l10n_cr_edi_payment_method_id.fiscal_position_id.map_tax(
                line.tax_ids._origin)

        return res
