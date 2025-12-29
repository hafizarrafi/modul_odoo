from odoo import models, fields, api
from odoo.exceptions import UserError

class RabManagementLine(models.Model):
    _name = 'rab.management.line'
    _description = 'RAB Line'

    rab_id = fields.Many2one(
        'rab.management',
        ondelete='cascade',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    name = fields.Char(
        string='Description',
        compute='_compute_name',
        store=True
    )

    quantity = fields.Float(
        default=1.0,
        digits='Product Unit of Measure'
    )


    # VENDOR COMPARISON
   
    vendor_line_ids = fields.One2many(
        'rab.vendor.comparison',
        'rab_line_id',
        string='Vendor Comparison'
    )

    chosen_vendor_id = fields.Many2one(
        'res.partner',
        string='Selected Vendor',
        readonly=True
    )

    purchase_price = fields.Monetary(
        string='Purchase Price',
        readonly=True
    )

    
    # MARGIN & PRICING
   
    margin_type = fields.Selection(
        [
            ('absolute', 'Absolute'),
            ('percentage', 'Percentage'),
        ],
        string='Margin Type',
        default='absolute',
        required=True
    )

    margin_value = fields.Float(
        string='Margin Value'
    )

    sale_price = fields.Monetary(
        string='Sale Price',
        compute='_compute_sale_price',
        store=True,
        readonly=True
    )

   
    # TOTAL
   
    subtotal = fields.Monetary(
        compute='_compute_subtotal',
        store=True
    )

    currency_id = fields.Many2one(
        related='rab_id.currency_id',
        store=True,
        readonly=True
    )

    is_locked = fields.Boolean(
    compute='_compute_is_locked',
    store=True
    )


    # METODE YANG MEMERLUKAN COMPUTE / OVERRIDE WRITE
   


    def write(self, vals):
        for rec in self:
            if rec.rab_id.state == 'approved':
                raise UserError(
                    "Approved RAB lines cannot be modified."
                )
        return super().write(vals)

    @api.depends('rab_id.state')
    def _compute_is_locked(self):
        for rec in self:
            rec.is_locked = rec.rab_id.state == 'approved'



    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name if line.product_id else ''

    @api.depends('purchase_price', 'margin_type', 'margin_value')
    def _compute_sale_price(self):
        for line in self:
            if not line.purchase_price:
                line.sale_price = 0.0
                continue

            if line.margin_type == 'absolute':
                line.sale_price = line.purchase_price + (line.margin_value or 0.0)

            elif line.margin_type == 'percentage':
                line.sale_price = line.purchase_price * (
                    1 + (line.margin_value or 0.0) / 100
                )

    @api.depends('quantity', 'sale_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.sale_price

  
    # ACTION OPEN RAB LINE

    def action_open_rab_line(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'RAB Line',
            'res_model': 'rab.management.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
