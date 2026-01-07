/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { VendorMatrix } from "../components/vendor_matrix/vendor_matrix";

export class RabVendorComparisonAction extends Component {
    setup() {
        // service bawaan odoo
        this.actionService = useService("action");
        this.notification = useService("notification");

        // ambil active_id dari context action
        this.rabId = this.props?.action?.context?.active_id;

        if (!this.rabId) {
            this.notification.add(
                "RAB ID tidak ditemukan.",
                { type: "danger" }
            );
        }
    }

    /**
     * Dipanggil setelah user memilih vendor final
     * (opsional, tapi rapi)
     */
    closeAndBack() {
        this.actionService.doAction({
            type: "ir.actions.act_window_close",
        });
    }
}

RabVendorComparisonAction.template =
    "rab_management.RabVendorComparisonAction";

RabVendorComparisonAction.components = {
    VendorMatrix,
};

// REGISTER ACTION
registry.category("actions").add(
    "rab_vendor_comparison_action",
    RabVendorComparisonAction
);
