from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    contact_type = fields.Selection(
        [
            ('supplier', 'Supplier'),
            ('customer', 'Customer'),
            ('both', 'Both'),
        ],
        string='Contact Type',
        required=True,
        default='customer',
    )
    @api.onchange('customer_rank', 'supplier_rank')
    def _onchange_sync_contact_type_from_rank(self):
        for partner in self:
            # kalau sudah ada contact_type, jangan ditimpa
            if partner.contact_type:
                continue

            if partner.customer_rank > 0 and partner.supplier_rank > 0:
                partner.contact_type = 'both'
            elif partner.customer_rank > 0:
                partner.contact_type = 'customer'
            elif partner.supplier_rank > 0:
                partner.contact_type = 'supplier'
        
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('contact_type'):
                customer_rank = vals.get('customer_rank', 0)
                supplier_rank = vals.get('supplier_rank', 0)

                if customer_rank > 0 and supplier_rank > 0:
                    vals['contact_type'] = 'both'
                elif customer_rank > 0:
                    vals['contact_type'] = 'customer'
                elif supplier_rank > 0:
                    vals['contact_type'] = 'supplier'
                else:
                    vals['contact_type'] = 'customer'

        return super().create(vals_list)

