from odoo import models, fields, api
from odoo.exceptions import UserError


class RabManagement(models.Model):
    _name = 'rab.management'
    _description = 'RAB Management'
    _order = 'id desc'

    # FIELDS YANG DIBUTUHKAN

    name = fields.Char(
        string='RAB Number',
        required=True,
        copy=False,
        default='New'
    )

    date = fields.Date(
        default=fields.Date.today
    )


# coba revisi
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting Approval'),
        ('revision', 'Revision'),
        ('approved', 'Approved'),
    ], default='draft', tracking=True
    )

    revision_note = fields.Text(
        string="Revision Note",
        tracking=True
    )



    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain=[('customer_rank', '>', 0)],
    )

    line_ids = fields.One2many(
        'rab.management.line',
        'rab_id',
        string='RAB Lines'
    )

    total_amount = fields.Monetary(
        compute='_compute_total',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        readonly=True
    )

    sale_order_ids = fields.One2many(
        'sale.order',
        compute='_compute_sale_orders',
        string='Sales Orders',
        readonly=True,
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        compute='_compute_purchase_orders',
        string='Purchase Orders',
        readonly=True,
    )

    


    # WORKFLOW YANG DISEDIAKAN
    def action_save_draft(self):
        self.ensure_one()
        self.write({})
        return True


    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                return

            if not rec.customer_id:
                raise UserError("Customer must be set.")

            if not rec.line_ids:
                raise UserError("Cannot confirm RAB without lines.")

            no_vendor_lines = rec.line_ids.filtered(
                lambda l: not l.chosen_vendor_id
            )
            if no_vendor_lines:
                raise UserError(
                    "All RAB lines must have a selected vendor before confirmation."
                )

            rec.state = 'confirmed'

    def action_send_for_approval(self):
        for rec in self:
            if rec.state not in ('confirmed', 'revision'):
                return
            rec.state = 'to_approve'

    def action_approve(self):
        for rec in self:
            if rec.state != 'to_approve':
                return

            if not self.env.user.has_group('base.group_system'):
                raise UserError("Only Administrator can approve RAB.")

            rec.state = 'approved'
    

    
    # PEMBUATAN SALES ORDER DARI RAB

    def action_create_sale_order(self):
        self.ensure_one()

        if self.state != 'approved':
            raise UserError("RAB must be approved before creating Sales Order.")

        if self.sale_order_id:
            raise UserError("Sales Order already created for this RAB.")

        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        so = SaleOrder.create({
            'partner_id': self.customer_id.id,
            'origin': self.name,
        })

        for line in self.line_ids:
            if not line.sale_price:
                raise UserError(
                    f"Sale price is not set for product {line.product_id.display_name}"
                )

            SaleOrderLine.create({
                'order_id': so.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.sale_price,
                'name': line.name,
            })

            self.with_context(allow_approved_write=True).write({
                'sale_order_id': so.id
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'res_id': so.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    
    # PEMBUATAN PURCHASE ORDER DARI RAB

    def action_create_purchase_orders(self):
        self.ensure_one()

        if self.state != 'approved':
            raise UserError("RAB must be approved before creating Purchase Orders.")

        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']

        # === KUMPULKAN LINE PER VENDOR ===
        vendor_map = {}

        for line in self.line_ids:
            if not line.chosen_vendor_id:
                raise UserError(
                    f"Line {line.product_id.display_name} has no selected vendor."
                )

            vendor = line.chosen_vendor_id
            vendor_map.setdefault(vendor, []).append(line)

        created_pos = self.env['purchase.order']

        # === BUAT PO PER VENDOR ===
        for vendor, lines in vendor_map.items():

            # PENGECEKAN DUPLIKAT PO DARI VENDOR YANG SAMA
            existing_po = PurchaseOrder.search([
                ('origin', '=', self.name),
                ('partner_id', '=', vendor.id),
            ], limit=1)

            if existing_po:
                raise UserError(
                    f"Purchase Order for vendor {vendor.display_name} already exists."
                )

            po = PurchaseOrder.create({
                'partner_id': vendor.id,
                'origin': self.name,
            })

            for line in lines:
                if not line.purchase_price:
                    raise UserError(
                        f"Purchase price not set for product {line.product_id.display_name}"
                    )

                PurchaseOrderLine.create({
                    'order_id': po.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_qty': line.quantity,
                    'price_unit': line.purchase_price,
                    'date_planned': fields.Date.today(),
                })

            created_pos |= po

        # TAMPILKAN DAFTAR PO YANG DIBUAT
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_pos.ids)],
        }

    
    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = self.env['sale.order'].search([
                ('origin', '=', rec.name)
            ])


    def _compute_purchase_orders(self):
        for rec in self:
            rec.purchase_order_ids = self.env['purchase.order'].search([
                ('origin', '=', rec.name)
            ])


 
    # KUNCI WRITE OVERRIDE KETIKA APPROVED

    def write(self, vals):
            for rec in self:
                if rec.state == 'approved':
                    if self.env.context.get('allow_approved_write'):
                        continue

                    forbidden_fields = set(vals.keys()) - {'sale_order_id'}
                    if forbidden_fields:
                        raise UserError("Approved RAB cannot be modified.")

            return super().write(vals)


 
    # COMPUTE
  
    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

  
    # SEQUENCE
   
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rab.management'
                ) or 'New'
        return super().create(vals_list)
    

    # coba fitur matrix vendor
    def action_open_vendor_matrix(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Matrix',
            'res_model': 'rab.vendor.comparison',
            'view_mode': 'pivot',
            'view_id': self.env.ref('rab_management.view_rab_vendor_comparison_pivot').id,
            'domain': [('rab_id', '=', self.id)],
            'target': 'current',  # atau 'new' kalau mau popup
        }
    
    # coba fitur revision
    def action_request_revision(self):
        self.ensure_one()
        self.state = 'revision'
