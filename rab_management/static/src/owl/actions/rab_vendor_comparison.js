/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { VendorMatrix } from "../components/vendor_matrix/vendor_matrix";

export class RabVendorComparisonAction extends Component {
    static template = "rab_management.RabVendorComparisonAction";
    static components = { VendorMatrix };

    setup() {
        const action = this.props.action;
        this.rabId = action.context?.active_id;

        console.log("RAB Vendor Comparison OWL loaded");
        console.log("RAB ID:", this.rabId);
    }
}

registry
    .category("actions")
    .add("rab_vendor_comparison_action", RabVendorComparisonAction);
