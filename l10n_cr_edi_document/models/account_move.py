# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from odoo import models, _
from odoo.tools import float_compare
from odoo.exceptions import UserError, ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    def xml2record(self, default_account=False):
        """Use the last attachment (xml) to fill the invoice data"""
        super().xml2record()
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        invoice = self
        for attachment in atts:
            xml = attachment.l10n_edi_document_is_xml()
            if not xml:
                continue
            invoice = self.env['account.move'].search([
                ('l10n_cr_edi_full_number', '=', xml['Clave'].text),
                ('state', 'in', ['posted', 'cancelled', 'draft']),
                ('move_type', '=', self.move_type),
            ]) or invoice
            if invoice != self:
                document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
                document.toggle_active()
                continue

            currency = self.env.ref('base.CRC')
            if hasattr(xml['ResumenFactura'], 'CodigoTipoMoneda'):
                currency_code = xml['ResumenFactura']['CodigoTipoMoneda']['CodigoMoneda']
                currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)

            # Set partner from xml
            partner_id = self.l10n_cr_edi_set_xml_partner(xml, currency)

            # set product lines
            action_post, invoice_lines = self.l10n_cr_edi_set_invoice_line(xml, partner_id, default_account)

            # set general information (Date, sequence, currency, and l10n_cr_edi info)
            action_post = self.l10n_cr_edi_set_xml_information(xml, currency, partner_id, invoice_lines)
            try:
                if action_post:
                    self.action_post()
            except (UserError, ValidationError) as exe:
                self.message_post(body=_(
                    '<b>Error on invoice validation </b><br/>%s') % exe.name)
                return self
            self.l10n_cr_edi_sat_status = 'signed'
        return invoice

    def l10n_cr_edi_set_invoice_line(self, xml, partner_id, default_account):
        prod_supplier = self.env['product.supplierinfo']
        prod = self.env['product.product']
        # FIXME CABYS Code required for December, 2020
        default_account = default_account or self.journal_id.default_account_id.id
        uom_obj = self.env['l10n_cr.uom']
        lines = []
        res = True
        for rec in xml['DetalleServicio']['LineaDetalle']:
            name = rec['Detalle'].text
            no_id = rec['CodigoComercial']['Codigo'] if hasattr(rec, 'CodigoComercial') else False
            uom = rec['UnidadMedida'].text
            qty = float(rec['Cantidad'])
            price = float(rec['PrecioUnitario'])
            amount = float(rec['MontoTotal'])
            supplierinfo = prod_supplier.search([
                '|', ('name', '=', self.partner_id.id),
                ('product_name', '=ilike', name)], limit=1)
            product = supplierinfo.product_tmpl_id.product_variant_id
            product = product or prod.search([
                '|', ('default_code', '=ilike', no_id),
                ('name', '=ilike', name)], limit=1)
            account_id = (
                product.property_account_expense_id.id or
                product.categ_id.property_account_expense_categ_id.id or
                default_account)

            discount = 0.0
            if hasattr(rec, 'Descuento') and amount:
                discount = ((float(rec['Descuento']['MontoDescuento'])) / amount) * 100

            domain_uom = [('code', '=', uom)]
            l10n_cr_edi_uom_id = uom_obj.search(domain_uom, limit=1)
            prod_uom_id = prod.search([('l10n_cr_edi_uom_id', '=', l10n_cr_edi_uom_id.id)], limit=1)
            uom_id = prod_uom_id.uom_id or self.env['uom.uom'].search([('name', '=', 'Units')])
            tax_line_ids, exonerations, message = self.get_line_taxes(rec)

            if message:
                res = False
            exoneration_id = False
            if exonerations:
                exoneration_id = self.l10n_cr_edi_set_xml_exoneration(partner_id, exonerations)

            lines.append((0, 0, {
                'product_id': product.id,
                'account_id': account_id,
                'name': name,
                'quantity': float(qty),
                'product_uom_id': uom_id.id,
                'tax_ids': tax_line_ids,
                'price_unit': float(price),
                'discount': discount,
                'l10n_cr_edi_tax_exemption_id': exoneration_id or False
            }))

        if message:
            self.message_post(
                body=_('The Following errors were found on Taxes:<br/>') +
                '<br/>'.join([f'{value}' for value in message.values()]))

        if not hasattr(xml, 'OtrosCargos'):
            return res, lines
        fiscal_position = self.fiscal_position_id
        for line in xml['OtrosCargos']:
            name = line['Detalle'].text
            code = line['TipoDocumento'].text
            product = prod.search([
                '|', ('default_code', '=', code),
                ('name', '=ilike', name)], limit=1)
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if self.is_sale_document(include_receipts=True):
                # Out invoice.
                account = accounts['income']
            elif self.is_purchase_document(include_receipts=True):
                # In invoice.
                account = accounts['expense']

            lines.append((0, 0, {
                'product_id': product.id,
                'account_id': account.id,
                'name': name,
                'quantity': 1,
                'product_uom_id': product.uom_id.id,
                'price_unit': float(line['MontoCargo']),
            }))
        return res, lines

    def l10n_cr_edi_get_address_information(self, partner_xml):
        xml_state = self.env['res.country.state']
        xml_canton = self.env['res.country.state.canton']
        xml_district = self.env['res.country.state.canton.district']
        xml_neighboarhood = self.env['res.country.state.canton.district.neighborhood']
        xml_street = ''
        if hasattr(partner_xml, 'Ubicacion'):
            if hasattr(partner_xml['Ubicacion'], 'Provincia'):
                xml_state = self.env['res.country.state'].search([
                    ("code", "=", partner_xml['Ubicacion']['Provincia']),
                ])

            if hasattr(partner_xml['Ubicacion'], 'Canton'):
                xml_canton = self.env['res.country.state.canton'].search([
                    ("code", "=", partner_xml['Ubicacion']['Canton']),
                    ("state_id", "=", xml_state.id),
                ])

            if hasattr(partner_xml['Ubicacion'], 'Distrito'):
                xml_district = self.env['res.country.state.canton.district'].search([
                    ("code", "=", partner_xml['Ubicacion']['Distrito']),
                    ("l10n_cr_edi_canton_id", "=", xml_canton.id),
                ])

            if hasattr(partner_xml['Ubicacion'], 'Barrio'):
                xml_neighboarhood = self.env['res.country.state.canton.district.neighborhood'].search([
                    ("code", "=", partner_xml['Ubicacion']['Barrio']),
                    ("district_id", "=", xml_district.id),
                ])

            xml_street += partner_xml['Ubicacion']['OtrasSenas'].text \
                if hasattr(partner_xml['Ubicacion'], 'OtrasSenas') else ''

        xml_street += partner_xml['OtrasSenasExtranjero'] if hasattr(partner_xml, 'OtrasSenasExtranjero') else ''
        country = self.env.ref('base.cr')
        xml_country = False
        if hasattr(partner_xml, 'Telefono'):
            country_code = partner_xml['Telefono']['CodigoPais'] if hasattr(
                partner_xml['Telefono'], 'CodigoPais') else False
            if country_code:
                xml_country = self.env['res.country'].search([('phone_code', '=', country_code)])
        return {
            'xml_state': xml_state.id or False,
            'xml_canton': xml_canton.id or False,
            'xml_district': xml_district.id or False,
            'xml_neighboarhood': xml_neighboarhood.id or False,
            'xml_street': xml_street,
            'xml_country': xml_country.id if xml_country else country.id,
        }

    def l10n_cr_edi_set_xml_partner(self, xml, currency):
        self.ensure_one()
        partner = self.env['res.partner']
        domain = []
        partner_xml = {}
        if self.move_type in ('out_invoice', 'out_refund'):
            partner_xml = xml['Receptor'] if hasattr(xml, 'Receptor') else False
            if not partner_xml:
                return False
            domain.append(('vat', '=', partner_xml['Identificacion']['Numero'].text if hasattr(
                partner_xml, 'Identificacion') else
                partner_xml['IdentificacionExtranjero'].text if hasattr(
                partner_xml, 'IdentificacionExtranjero') else False))
        elif self.move_type in ('in_invoice', 'in_refund'):
            partner_xml = xml['Emisor']
            domain.append(('vat', '=', partner_xml['Identificacion']['Numero']))
        domain.append(('is_company', '=', True))
        xml_partner = partner.search(domain, limit=1)
        currency_field = 'property_purchase_currency_id' in partner._fields
        if currency_field:
            domain.append(('property_purchase_currency_id', '=', currency.id))
        if currency_field and not xml_partner:
            domain.pop()
            xml_partner = partner.search(domain, limit=1)
        if not xml_partner:
            domain.pop()
            xml_partner = partner.search(domain, limit=1)

        if xml_partner:
            return xml_partner

        xml_id = partner_xml['Identificacion'] if hasattr(partner_xml, 'Identificacion') else False
        vat = ''
        vat_type = False
        if hasattr(xml_id, 'Numero'):
            vat = xml_id['Numero'].text
            vat_type = xml_id['Tipo'].text
        if hasattr(xml_id, 'IdentificacionExtranjero'):
            vat = xml_id['IdentificacionExtranjero'].text
            vat_type = 'XX'
        address = self.l10n_cr_edi_get_address_information(partner_xml)
        xml_phone = partner_xml['Telefono']['NumTelefono'] if hasattr(
            partner_xml, 'Telefono') and hasattr(partner_xml['Telefono'], 'NumTelefono') else False
        xml_partner = partner.create({
            'company_type': 'company',
            'name': partner_xml['Nombre'],
            'country_id': address['xml_country'],
            'state_id': address['xml_state'],
            'l10n_cr_edi_canton_id': address['xml_canton'],
            'l10n_cr_edi_district_id': address['xml_district'],
            'l10n_cr_edi_neighborhood_id': address['xml_neighboarhood'],
            'street': address['xml_street'],
            'phone': xml_phone,
            'email': partner_xml['CorreoElectronico'] if hasattr(partner_xml, 'CorreoElectronico') else False,
            'vat': vat,
            'l10n_cr_edi_vat_type': vat_type,
        })
        xml_partner.message_post(body=_(
            'This record was generated from DMS'))
        return xml_partner

    def get_line_taxes(self, line):
        taxes_list = []
        if not hasattr(line, 'Impuesto'):
            return [False, False, False]
        tax_xml = line['Impuesto']
        exonerations = []
        taxes = self.collect_taxes(tax_xml)
        res = True
        message = {}
        for tax in taxes:
            exonerations = []
            type_tax = 'purchase' if 'in_' in self.move_type else 'sale'
            domain = [
                ('type_tax_use', '=', type_tax),
                ('company_id', 'in', (False, self.company_id.id)),
                ('amount', '=', tax['amount']), ('l10n_cr_edi_code', '=', tax['tax']),
                ('l10n_cr_edi_iva_code', '=', tax['rate']), ('l10n_cr_edi_exempt', '=', tax['exoneration'])
            ]
            if tax['exoneration']:
                exonerations.append(tax['invoice_exononeration'])
                domain += [('l10n_cr_edi_original_amount', '=', float(tax['original_amount']))]

            tax_get = self.env['account.tax'].search(domain, limit=1)
            if not tax_get:
                if not tax['rate'] in message:
                    message[tax['amount']] = (
                        _('The tax for %s with amount %s cannot be found') % (type_tax, tax['amount']))
                res = False
            tax_account = tax_get.invoice_repartition_line_ids.filtered(
                lambda rec: rec.repartition_type == 'tax')
            if tax_get and not tax_account:
                if 'account' not in message:
                    message['account'] = (_('Please configure the tax account in the tax'))
                res = False
            taxes_list.append((4, tax_get.id))
        return taxes_list if res else False, exonerations, message

    def collect_taxes(self, taxes_xml):
        """ Get tax data of the Impuesto node of the xml and return
        dictionary with taxes datas
        :param taxes_xml: Impuesto node of xml
        :type taxes_xml: etree
        :return: A list with the taxes data
        :rtype: list
        """
        taxes = []
        invoice_exononeration = {}
        exoneration_xml = False
        original_amount_xml = None
        for rec in taxes_xml:
            tax_xml = rec['Codigo'].text
            rate_xml = rec['CodigoTarifa'].text
            amount_xml = float(rec['Tarifa'].text)

            if hasattr(taxes_xml, 'Exoneracion'):
                original_amount_xml = rec['Tarifa']
                amount_xml = int(original_amount_xml) - int(rec['Exoneracion']['PorcentajeExoneracion'])
                exoneration_xml = True
                invoice_exononeration.update({
                    'l10n_cr_edi_exempt_type': rec['Exoneracion']['TipoDocumento'].text,
                    'l10n_cr_edi_exempt_num': rec['Exoneracion']['NumeroDocumento'].text,
                    'l10n_cr_edi_exempt_issuer': rec['Exoneracion']['NombreInstitucion'].text,
                    'l10n_cr_edi_exempt_date': self.get_date_in_different_formats(
                        rec['Exoneracion']['FechaEmision'].text),
                })

            taxes.append({
                'tax': tax_xml, 'rate': rate_xml, 'amount': amount_xml,
                'exoneration': exoneration_xml, 'original_amount': original_amount_xml,
                'invoice_exononeration': invoice_exononeration
            })
        return taxes

    def get_date_in_different_formats(self, date):
        format_code = '%Y-%m-%d'
        try:
            return datetime.strptime(date, format_code)
        except ValueError:
            format_code = '%Y-%m-%dT%H:%M:%S-06:00'

        try:
            return datetime.strptime(date, format_code)
        except ValueError:
            format_code = '%Y-%m-%dT%H:%M:%S'

        try:
            return datetime.strptime(date, format_code)
        except ValueError:
            # To remove any format like %Y-%m-%dT%H:%M:%S.SSSSSSS
            date = date[:19]
        try:
            return datetime.strptime(date, format_code)
        except ValueError:
            return False

    def l10n_cr_edi_set_xml_exoneration(self, partner_id, exonerations):
        domain = [
            ('exempt_type', '=', exonerations[0]['l10n_cr_edi_exempt_type']),
            ('name', '=', exonerations[0]['l10n_cr_edi_exempt_num']),
            ('active', 'in', (False, True)),
        ]
        exoneration_id = self.env['l10n_cr_edi.tax.exemption'].search(domain, limit=1)
        if not exoneration_id:
            exoneration_id = self.env['l10n_cr_edi.tax.exemption'].create({
                'exempt_type': exonerations[0]['l10n_cr_edi_exempt_type'],
                'name': exonerations[0]['l10n_cr_edi_exempt_num'],
                'issuer': exonerations[0]['l10n_cr_edi_exempt_issuer'],
                'exempt_date': exonerations[0]['l10n_cr_edi_exempt_date'],
                'partner_id': partner_id.id,
                'active': False,
            })
        return exoneration_id

    def l10n_cr_edi_set_xml_information(self, xml, currency, partner_id, invoice_lines):
        self.ensure_one()
        invoice_data = {}

        invoice_date = self.get_date_in_different_formats(xml['FechaEmision'].text)

        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        invoice_type = 'sale' if self.move_type == 'out_invoice' else 'purchase'

        invoice_name = xml['NumeroConsecutivo'].text
        economic_activity = self._get_default_l10n_cr_edi_economic_activity()
        if invoice_type == 'sale':
            economic_activity = self.env['l10n.cr.account.invoice.economic.activity'].search([
                ('code', '=', xml['CodigoActividad'].text),
            ]).id
            invoice_data.update({
                'l10n_cr_edi_xml_binary': attachment.datas,
                'l10n_cr_edi_xml_filename': attachment.name,
                'l10n_cr_edi_sat_status': 'accepted',
            })
        else:
            invoice_count = self.env['account.move'].search_count([
                ('name', '=', invoice_name), ('move_type', '=', self.move_type),
            ])
            if invoice_count:
                invoice_name = '%s/%s' % (invoice_name, str(invoice_count).zfill(3))
            invoice_data.update({
                'l10n_cr_edi_xml_customer_binary': attachment.datas,
                'l10n_cr_edi_xml_customer_filename': attachment.name,
            })

        invoice_data.update({
            'invoice_date': invoice_date,
            'date': invoice_date,
            'l10n_cr_edi_emission_datetime': invoice_date,
            'currency_id': currency.id,
            'l10n_cr_edi_full_number': xml['Clave'].text,
            'l10n_cr_edi_economic_activity_id': economic_activity or False,
            'l10n_cr_edi_security_code': xml['Clave'].text[42:],
            'partner_id': partner_id,
            'invoice_line_ids': invoice_lines,
            'name': invoice_name,
        })

        self.write(invoice_data)
        self._onchange_partner_id()
        difference = abs(float(xml['ResumenFactura']['TotalComprobante']) - self.amount_total)
        if difference:
            sign = float_compare(float(xml['ResumenFactura']['TotalComprobante']),
                                 self.amount_total, precision_digits=5)
            round_limit = self.env[
                'ir.config_parameter'
            ].sudo().get_param('l10n_cr_edi_document.rounding_adjustment_limit')
            if difference > float(round_limit):
                self.message_post(
                    body=_('Rounding difference against XML information, please check the invoice Total amount.'))
                self._recompute_dynamic_lines()
                return False

            name = 'Ajuste de redondeo'
            fiscal_position = self.fiscal_position_id
            product = self.env.ref('l10n_cr_edi.product_other_charges_other')
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if self.is_sale_document(include_receipts=True):
                # Out invoice.
                account = accounts['income']
            elif self.is_purchase_document(include_receipts=True):
                # In invoice.
                account = accounts['expense']

            self.write({
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'account_id': account.id,
                    'name': name,
                    'quantity': 1,
                    'product_uom_id': product.uom_id.id,
                    'price_unit': sign * difference,
                })]
            })

        self._recompute_dynamic_lines()
        if not economic_activity:
            self.message_post(
                body=_('Economic activity not found. Please check the Economic Activities configuration.'))
            return False
        return True
