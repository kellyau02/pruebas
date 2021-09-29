odoo.define('l10n_cr_einvoicing_pos_base.vat_type', function (require) {
    "use strict";
    var core = require('web.core');
    var _t = core._t;

    var models = require('point_of_sale.models');
    models.load_fields('res.partner', [
        'email_copies',
        'vat_type',
        'state_id',
        'canton_id',
        'district_id',
        'neighborhood_id']);

    var screens = require('point_of_sale.screens');
    screens.PaymentScreenWidget.include({
        finalize_validation: function () {
            var self = this;
            var order = this.pos.get_order();

            if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

                this.pos.proxy.open_cashbox();
            }

            order.initialize_validation_date();
            order.finalized = true;

            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.fail(function (error) {
                    self.invoicing = false;
                    order.finalized = false;
                    if (error.message === 'Missing Customer') {
                        self.gui.show_popup('confirm', {
                            'title': _t('Please select the Customer'),
                            'body': _t('You need to select the customer \
                                       before you can invoice an order.'),
                            confirm: function(){
                                self.gui.show_screen('clientlist');
                            },
                        });
                    } else if (error.code < 0) {        // XmlHttpRequest Errors
                        self.gui.show_popup('error',{
                            'title': _t('The order could not be sent'),
                            'body': _t('Check your internet connection and try again.'),
                        });
                    } else if (error.code === 200) {    // OpenERP Server Errors
                        self.gui.show_popup('error-traceback',{
                            'title': error.data.message || _t("Server Error"),
                            'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
                        });
                    } else {                            // ???
                        self.gui.show_popup('error',{
                            'title': _t("Unknown Error"),
                            'body':  _t("The order could not be sent to the server due to an unknown error"),
                        });
                    }
                });

                invoiced.done(function(){
                    self.invoicing = false;
                    var params = {
                        model: 'pos.order',
                        context: {},
                        method: 'search_read',
                        domain: [['pos_reference','=',order.get_name()]],
                        fields: ['invoice_number','invoice_cr_einvoicing_full_number'],
                    }
                    rpc.query(params).then(function(data){
                        if (data && data.length > 0){
                            order.invoice_number = data[0].invoice_number;
                            order.invoice_cr_einvoicing_full_number = data[0].invoice_cr_einvoicing_full_number;
                            self.gui.show_screen('receipt');
                        }
                    });
                });
            } else {
                this.pos.push_order(order);
                var params = {
                    model: 'pos.order',
                    context: {},
                    method: 'search_read',
                    domain: [['pos_reference','=',order.get_name()]],
                    fields: ['invoice_number','invoice_cr_einvoicing_full_number'],
                }
                rpc.query(params).then(function(data){
                    if (data && data.length > 0){
                        order.invoice_number = data[0].invoice_number;
                        order.invoice_cr_einvoicing_full_number = data[0].invoice_cr_einvoicing_full_number;
                        self.gui.show_screen('receipt');
                    }
                });
            }

        }
    });

    var rpc = require('web.rpc');
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function(){
            var receipt = _super_order.export_for_printing.apply(this, arguments);
            var client  = this.get('client');
            receipt.invoice_number = this.invoice_number;
            receipt.invoice_cr_einvoicing_full_number = this.invoice_cr_einvoicing_full_number;
            receipt.client_vat = client ? client.vat: null;
            receipt.client_email = client ? client.email: null;
            return receipt
        }
    });
});
