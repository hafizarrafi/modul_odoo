/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class VendorMatrix extends Component {
    setup() {
        this.state = useState({
            vendors: [],
            items: [],
            loading: true,
        });

        this.rabService = useService("rabService");

        onWillStart(async () => {
            await this.reloadMatrix();
            this.state.loading = false;
        });
    }

    async reloadMatrix() {
        const { lines, vendorLines } =
            await this.rabService.fetchVendorMatrix(this.props.rabId);
        this.buildMatrix(lines, vendorLines);
    }

    buildMatrix(lines, vendorLines) {
        const vendorMap = {};
        const itemMap = {};

        for (const line of lines) {
            itemMap[line.id] = {
                id: line.id,
                name: line.product_id[1],
                qty: line.quantity,
                prices: {},
            };
        }

        for (const v of vendorLines) {
            const lineId = v.rab_line_id[0];
            const vendorId = v.vendor_id[0];

            vendorMap[vendorId] ??= {
                id: vendorId,
                name: v.vendor_id[1],
            };

            itemMap[lineId].prices[vendorId] = {
                id: v.id,
                base: v.price,
                nego: v.negotiation_price,
                vendor_state: v.vendor_state,
            };
        }

        this.state.vendors = Object.values(vendorMap);
        this.state.items = Object.values(itemMap);
    }

    async onSetNegotiation(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        await this.rabService.setNegotiation(id);
        await this.reloadMatrix();
    }

    async onSelectVendor(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        await this.rabService.setFinalVendor(id);
        await this.reloadMatrix();
    }

    formatPrice(value) {
        return value ? value.toLocaleString("id-ID") : "-";
    }
}

VendorMatrix.template = "rab_management.VendorMatrix";
