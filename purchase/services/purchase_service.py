from datetime import datetime
from django.db import transaction, models
from purchase.models.purchase_order import PurchaseOrder
from purchase.models.purchase_order_item import PurchaseOrderItem
from purchase.models.purchase_invoice import PurchaseInvoice
from purchase.models.purchase_invoice_item import PurchaseInvoiceItem
from .stock_service import StockService


class PurchaseService:

    @classmethod
    def generate_po_number(cls, restaurant):
        """Generate next PO number in format PO-YYMM-NNN."""
        now = datetime.now()
        prefix = f"PO-{now.strftime('%y%m')}-"
        last_po = (
            PurchaseOrder.objects.filter(
                restaurant=restaurant,
                order_number__startswith=prefix,
            )
            .order_by("-order_number")
            .first()
        )
        if last_po:
            try:
                last_num = int(last_po.order_number.split("-")[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        return f"{prefix}{next_num:03d}"

    @classmethod
    def approve_order(cls, purchase_order, user=None):
        """Transition PO from DRAFT to APPROVED."""
        if purchase_order.status != PurchaseOrder.Status.DRAFT.value:
            raise ValueError("Only DRAFT orders can be approved.")
        if not purchase_order.items.filter(is_deleted=False).exists():
            raise ValueError("Cannot approve a purchase order with no items.")
        purchase_order.status = PurchaseOrder.Status.APPROVED.value
        purchase_order.updated_by = user
        purchase_order.save(update_fields=["status", "updated_by", "updated_at"])

    @classmethod
    @transaction.atomic
    def receive_order(cls, purchase_order, user=None, auto_create_invoice=False):
        """
        Transition PO from APPROVED to RECEIVED.
        Optionally auto-creates a PurchaseInvoice with stock entries.
        """
        if purchase_order.status != PurchaseOrder.Status.APPROVED.value:
            raise ValueError("Only APPROVED orders can be received.")
        purchase_order.status = PurchaseOrder.Status.RECEIVED.value
        purchase_order.updated_by = user
        purchase_order.save(update_fields=["status", "updated_by", "updated_at"])

        if auto_create_invoice:
            invoice = cls.create_invoice_from_po(
                purchase_order,
                invoice_number=f"FROM-PO-{purchase_order.order_number}",
                invoice_date=purchase_order.order_date,
                user=user,
            )
            return invoice
        return None

    @classmethod
    def cancel_order(cls, purchase_order, user=None):
        """Cancel a PO (only from DRAFT or APPROVED states)."""
        allowed = [
            PurchaseOrder.Status.DRAFT.value,
            PurchaseOrder.Status.APPROVED.value,
        ]
        if purchase_order.status not in allowed:
            raise ValueError("Only DRAFT or APPROVED orders can be cancelled.")
        purchase_order.status = PurchaseOrder.Status.CANCELLED.value
        purchase_order.updated_by = user
        purchase_order.save(update_fields=["status", "updated_by", "updated_at"])

    @classmethod
    @transaction.atomic
    def create_invoice_from_po(cls, purchase_order, invoice_number, invoice_date, user=None):
        """
        Create a PurchaseInvoice pre-populated from PO line items.
        Also creates stock entries via StockService.
        """
        invoice = PurchaseInvoice.objects.create(
            restaurant=purchase_order.restaurant,
            vendor=purchase_order.vendor,
            purchase_order=purchase_order,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            sub_total=purchase_order.sub_total,
            total_amount=purchase_order.total_amount,
            updated_by=user,
        )

        for po_item in purchase_order.get_items():
            PurchaseInvoiceItem.objects.create(
                purchase_invoice=invoice,
                inventory_item=po_item.inventory_item,
                item_name=po_item.item_name,
                unit=po_item.unit,
                quantity=po_item.quantity,
                unit_price=po_item.unit_price,
                tax_percent=po_item.tax_percent,
                amount=po_item.amount,
                updated_by=user,
            )

        StockService.add_stock_from_invoice(invoice, user=user)
        return invoice

    @classmethod
    def recalculate_order_totals(cls, purchase_order):
        """Recompute sub_total, tax_amount, total_amount from line items."""
        items = purchase_order.items.filter(is_deleted=False)
        agg = items.aggregate(
            sub=models.Sum(
                models.F("quantity") * models.F("unit_price"),
                output_field=models.DecimalField(),
            ),
            total=models.Sum("amount"),
        )
        sub_total = agg["sub"] or 0
        total_amount = agg["total"] or 0
        tax_amount = total_amount - sub_total

        purchase_order.sub_total = sub_total
        purchase_order.tax_amount = tax_amount
        purchase_order.total_amount = total_amount
        purchase_order.save(
            update_fields=["sub_total", "tax_amount", "total_amount", "updated_at"]
        )

    @classmethod
    def recalculate_invoice_totals(cls, purchase_invoice):
        """Recompute sub_total, total_amount from invoice line items."""
        items = purchase_invoice.items.filter(is_deleted=False)
        agg = items.aggregate(
            sub=models.Sum(
                models.F("quantity") * models.F("unit_price"),
                output_field=models.DecimalField(),
            ),
            total=models.Sum("amount"),
        )
        sub_total = agg["sub"] or 0
        total_amount = agg["total"] or 0

        purchase_invoice.sub_total = sub_total
        purchase_invoice.total_amount = total_amount - purchase_invoice.discount
        purchase_invoice.save(
            update_fields=["sub_total", "total_amount", "updated_at"]
        )
