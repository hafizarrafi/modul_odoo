from odoo import models, fields, api
from odoo.exceptions import UserError


class RabManagement(models.Model):
    _name = 'rab.management'
    _description = 'RAB Management'
    _order = 'id desc'

    # ------------------------------------------------------------------
    # Informasi dasar RAB
    # ------------------------------------------------------------------

    name = fields.Char(
        string='Nomor RAB',
        required=True,
        copy=False,
        default='New'
    )

    date = fields.Date(
        string='Tanggal',
        default=fields.Date.today
    )

    # Status workflow RAB
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('to_approve', 'Menunggu Persetujuan'),
            ('revision', 'Revisi'),
            ('approved', 'Disetujui'),
        ],
        default='draft',
        tracking=True
    )

    # Catatan revisi dari approver
    revision_note = fields.Text(
        string="Catatan Revisi",
        tracking=True
    )

    # Customer tujuan penawaran
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain=[('contact_type', 'in', ['customer', 'both'])],
    )

    # ------------------------------------------------------------------
    # Detail RAB
    # ------------------------------------------------------------------

    line_ids = fields.One2many(
        'rab.management.line',
        'rab_id',
        string='Detail RAB'
    )

    total_amount = fields.Monetary(
        string='Total',
        compute='_compute_total',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ------------------------------------------------------------------
    # Relasi ke dokumen turunan
    # ------------------------------------------------------------------

    # Sales Order utama yang dibuat dari RAB
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        readonly=True
    )

    # Semua Sales Order yang berasal dari RAB ini
    sale_order_ids = fields.One2many(
        'sale.order',
        compute='_compute_sale_orders',
        string='Sales Orders',
        readonly=True,
    )

    # Semua Purchase Order yang berasal dari RAB ini
    purchase_order_ids = fields.One2many(
        'purchase.order',
        compute='_compute_purchase_orders',
        string='Purchase Orders',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_save_draft(self):
        """Digunakan untuk menyimpan ulang RAB tanpa mengubah state."""
        self.ensure_one()
        self.write({})
        return True

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                return

            # Validasi dasar sebelum konfirmasi
            if not rec.customer_id:
                raise UserError("Customer harus diisi.")

            if not rec.line_ids:
                raise UserError("RAB tidak dapat dikonfirmasi tanpa detail.")

            # Semua baris harus sudah memiliki vendor terpilih
            no_vendor_lines = rec.line_ids.filtered(
                lambda l: not l.chosen_vendor_id
            )
            if no_vendor_lines:
                raise UserError(
                    "Semua baris RAB harus memiliki vendor terpilih sebelum konfirmasi."
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

            # Contoh pembatasan hak approve (sementara: admin saja)
            if not self.env.user.has_group('base.group_system'):
                raise UserError("Hanya Administrator yang dapat menyetujui RAB.")

            rec.state = 'approved'

    def action_request_revision(self):
        """Mengembalikan RAB ke tahap revisi."""
        self.ensure_one()
        self.state = 'revision'

    # ------------------------------------------------------------------
    # Pembuatan Sales Order dari RAB
    # ------------------------------------------------------------------

    def action_create_sale_order(self):
        self.ensure_one()

        if self.state != 'approved':
            raise UserError("RAB harus disetujui sebelum membuat Sales Order.")

        if self.sale_order_id:
            raise UserError("Sales Order untuk RAB ini sudah dibuat.")

        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        # Buat SO header
        so = SaleOrder.create({
            'partner_id': self.customer_id.id,
            'origin': self.name,
        })

        # Buat SO line dari setiap baris RAB
        for line in self.line_ids:
            if not line.sale_price:
                raise UserError(
                    f"Harga jual belum ditentukan untuk produk {line.product_id.display_name}"
                )

            SaleOrderLine.create({
                'order_id': so.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.sale_price,
                'name': line.name,
            })

        # Simpan referensi SO ke RAB (diizinkan meski RAB sudah approved)
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

    # ------------------------------------------------------------------
    # Pembuatan Purchase Order dari RAB
    # ------------------------------------------------------------------

    def action_create_purchase_orders(self):
        self.ensure_one()

        if self.state != 'approved':
            raise UserError("RAB harus disetujui sebelum membuat Purchase Order.")

        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']

        # Kelompokkan baris RAB berdasarkan vendor
        vendor_map = {}

        for line in self.line_ids:
            if not line.chosen_vendor_id:
                raise UserError(
                    f"Produk {line.product_id.display_name} belum memiliki vendor terpilih."
                )

            vendor = line.chosen_vendor_id
            vendor_map.setdefault(vendor, []).append(line)

        created_pos = self.env['purchase.order']

        # Buat satu PO untuk setiap vendor
        for vendor, lines in vendor_map.items():

            # Cegah duplikasi PO untuk vendor yang sama
            existing_po = PurchaseOrder.search([
                ('origin', '=', self.name),
                ('partner_id', '=', vendor.id),
            ], limit=1)

            if existing_po:
                raise UserError(
                    f"Purchase Order untuk vendor {vendor.display_name} sudah ada."
                )

            po = PurchaseOrder.create({
                'partner_id': vendor.id,
                'origin': self.name,
            })

            for line in lines:
                if not line.purchase_price:
                    raise UserError(
                        f"Harga beli belum ditentukan untuk produk {line.product_id.display_name}"
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

        # Tampilkan daftar PO yang berhasil dibuat
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_pos.ids)],
        }

    # ------------------------------------------------------------------
    # Compute helpers
    # ------------------------------------------------------------------

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

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    # ------------------------------------------------------------------
    # Proteksi write saat RAB sudah disetujui
    # ------------------------------------------------------------------

    def write(self, vals):
        for rec in self:
            if rec.state == 'approved':
                # Izinkan update terbatas (misalnya set sale_order_id)
                if self.env.context.get('allow_approved_write'):
                    continue

                forbidden_fields = set(vals.keys()) - {'sale_order_id'}
                if forbidden_fields:
                    raise UserError("RAB yang sudah disetujui tidak dapat diubah.")

        return super().write(vals)

    # ------------------------------------------------------------------
    # Sequence
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rab.management'
                ) or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Tampilan matrix vendor (pivot)
    # ------------------------------------------------------------------

    def action_open_vendor_matrix(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Matriks Vendor',
            'res_model': 'rab.vendor.comparison',
            'view_mode': 'pivot',
            'view_id': self.env.ref(
                'rab_management.view_rab_vendor_comparison_pivot'
            ).id,
            'domain': [('rab_id', '=', self.id)],
            'target': 'current',
        }
