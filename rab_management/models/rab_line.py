from odoo import models, fields, api


class RabManagementLine(models.Model):
    _name = 'rab.management.line'
    _description = 'RAB Line'

    rab_id = fields.Many2one(
        'rab.management',
        ondelete='cascade',
        required=True
    )

    name = fields.Char(
        string='Description',
        required=True
    )

    quantity = fields.Float(
        default=1.0
    )

    price_unit = fields.Monetary(
        string='Unit Price'
    )

    subtotal = fields.Monetary(
        compute='_compute_subtotal',
        store=True
    )

    currency_id = fields.Many2one(
        related='rab_id.currency_id',
        store=True,
        readonly=True
    )
    quantity = fields.Float(
    default=1.0,
    digits='Product Unit of Measure'
    )


    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
