from datetime import date
from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group

from core.models.restaurant import Restaurant
from core.models.staff import Staff
from purchase.models import (
    Vendor,
    Customer,
    ExpenseCategory,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    StockEntry,
    Payment,
    Expense,
)
from purchase.services.stock_service import StockService
from purchase.services.purchase_service import PurchaseService
from purchase.services.payment_service import PaymentService
from purchase.services.finance_summary_service import FinanceSummaryService


class PurchaseTestBase(TestCase):
    """Base test class with common fixtures."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant", display_name="Test Restaurant"
        )

        # Create owner user + staff
        self.owner_user = User.objects.create_user(
            username="owner", password="testpass123"
        )
        owner_group, _ = Group.objects.get_or_create(name="OWNER")
        self.owner_user.groups.add(owner_group)
        self.owner_staff = Staff.objects.create(
            user=self.owner_user, restaurant=self.restaurant
        )

        # Create manager user + staff
        self.manager_user = User.objects.create_user(
            username="manager", password="testpass123"
        )
        manager_group, _ = Group.objects.get_or_create(name="MANAGER")
        self.manager_user.groups.add(manager_group)
        self.manager_staff = Staff.objects.create(
            user=self.manager_user, restaurant=self.restaurant
        )

        # Create waiter user + staff
        self.waiter_user = User.objects.create_user(
            username="waiter", password="testpass123"
        )
        waiter_group, _ = Group.objects.get_or_create(name="WAITER")
        self.waiter_user.groups.add(waiter_group)
        self.waiter_staff = Staff.objects.create(
            user=self.waiter_user, restaurant=self.restaurant
        )


# ──────────────────────────────────────────────
# MODEL TESTS
# ──────────────────────────────────────────────


class VendorModelTest(PurchaseTestBase):

    def test_create_vendor(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant,
            name="Fresh Farms",
            phone="9876543210",
            gstin="22AAAAA0000A1Z5",
        )
        self.assertEqual(vendor.name, "Fresh Farms")
        self.assertFalse(vendor.is_deleted)

    def test_soft_delete_vendor(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Test Vendor"
        )
        vendor.soft_delete(self.owner_user)
        self.assertTrue(vendor.is_deleted)
        self.assertIsNone(
            Vendor.get_vendor_by_id(vendor.id, self.restaurant)
        )

    def test_unique_vendor_name_per_restaurant(self):
        Vendor.objects.create(restaurant=self.restaurant, name="Unique Vendor")
        with self.assertRaises(Exception):
            Vendor.objects.create(
                restaurant=self.restaurant, name="Unique Vendor"
            )

    def test_get_vendors_for_restaurant(self):
        Vendor.objects.create(restaurant=self.restaurant, name="Vendor A")
        Vendor.objects.create(restaurant=self.restaurant, name="Vendor B")
        vendors = Vendor.get_vendors_for_restaurant(self.restaurant)
        self.assertEqual(vendors.count(), 2)


class CustomerModelTest(PurchaseTestBase):

    def test_create_customer(self):
        customer = Customer.objects.create(
            restaurant=self.restaurant,
            name="John Doe",
            phone="1234567890",
            credit_limit=Decimal("5000.00"),
        )
        self.assertEqual(customer.name, "John Doe")
        self.assertEqual(customer.credit_limit, Decimal("5000.00"))

    def test_get_customer_by_phone(self):
        Customer.objects.create(
            restaurant=self.restaurant, name="Jane", phone="9999999999"
        )
        customer = Customer.get_customer_by_phone("9999999999", self.restaurant)
        self.assertIsNotNone(customer)
        self.assertEqual(customer.name, "Jane")


class InventoryItemModelTest(PurchaseTestBase):

    def test_create_inventory_item(self):
        item = InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Tomatoes",
            unit=InventoryItem.Unit.KG.value,
            current_stock=Decimal("50.000"),
            low_stock_threshold=Decimal("10.000"),
            cost_per_unit=Decimal("40.00"),
        )
        self.assertEqual(item.stock_value, Decimal("2000.000"))
        self.assertFalse(item.is_low_stock)

    def test_low_stock_detection(self):
        item = InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Onions",
            unit=InventoryItem.Unit.KG.value,
            current_stock=Decimal("5.000"),
            low_stock_threshold=Decimal("10.000"),
        )
        self.assertTrue(item.is_low_stock)

    def test_get_low_stock_items(self):
        InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Item OK",
            current_stock=Decimal("100.000"),
            low_stock_threshold=Decimal("10.000"),
        )
        InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Item Low",
            current_stock=Decimal("5.000"),
            low_stock_threshold=Decimal("10.000"),
        )
        low = InventoryItem.get_low_stock_items(self.restaurant)
        self.assertEqual(low.count(), 1)
        self.assertEqual(low.first().name, "Item Low")


class PurchaseOrderModelTest(PurchaseTestBase):

    def test_create_purchase_order(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Supplier A"
        )
        po = PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            vendor=vendor,
            order_number="PO-2602-001",
            order_date=date.today(),
        )
        self.assertEqual(po.status, PurchaseOrder.Status.DRAFT.value)

    def test_filter_by_status(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Supplier B"
        )
        PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            vendor=vendor,
            order_number="PO-001",
            order_date=date.today(),
            status=PurchaseOrder.Status.DRAFT.value,
        )
        PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            vendor=vendor,
            order_number="PO-002",
            order_date=date.today(),
            status=PurchaseOrder.Status.APPROVED.value,
        )
        drafts = PurchaseOrder.get_orders_for_restaurant(
            self.restaurant, status_filter=PurchaseOrder.Status.DRAFT.value
        )
        self.assertEqual(drafts.count(), 1)


class PurchaseInvoiceModelTest(PurchaseTestBase):

    def test_balance_due(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Supplier C"
        )
        invoice = PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=vendor,
            invoice_number="INV-001",
            invoice_date=date.today(),
            total_amount=Decimal("5000.00"),
            amount_paid=Decimal("2000.00"),
        )
        self.assertEqual(invoice.balance_due, Decimal("3000.00"))


# ──────────────────────────────────────────────
# SERVICE TESTS
# ──────────────────────────────────────────────


class StockServiceTest(PurchaseTestBase):

    def setUp(self):
        super().setUp()
        self.item = InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Rice",
            unit=InventoryItem.Unit.KG.value,
            current_stock=Decimal("100.000"),
            cost_per_unit=Decimal("60.00"),
        )

    def test_manual_add_stock(self):
        StockService.manual_stock_adjustment(
            inventory_item=self.item,
            quantity=Decimal("50.000"),
            entry_type=StockEntry.EntryType.MANUAL_ADD.value,
            restaurant=self.restaurant,
            user=self.owner_user,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("150.000"))

    def test_manual_remove_stock(self):
        StockService.manual_stock_adjustment(
            inventory_item=self.item,
            quantity=Decimal("30.000"),
            entry_type=StockEntry.EntryType.MANUAL_REMOVE.value,
            restaurant=self.restaurant,
            user=self.owner_user,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("70.000"))

    def test_usage_makes_quantity_negative(self):
        entry = StockService.manual_stock_adjustment(
            inventory_item=self.item,
            quantity=Decimal("20.000"),
            entry_type=StockEntry.EntryType.USAGE.value,
            restaurant=self.restaurant,
        )
        self.assertTrue(entry.quantity < 0)

    def test_add_stock_from_invoice(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Rice Supplier"
        )
        invoice = PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=vendor,
            invoice_number="INV-RICE-001",
            invoice_date=date.today(),
            total_amount=Decimal("3000.00"),
        )
        PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            inventory_item=self.item,
            item_name=self.item.name,
            unit=self.item.unit,
            quantity=Decimal("50.000"),
            unit_price=Decimal("60.00"),
            amount=Decimal("3000.00"),
        )
        entries = StockService.add_stock_from_invoice(invoice, user=self.owner_user)
        self.assertEqual(len(entries), 1)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("150.000"))

    def test_get_total_stock_value(self):
        value = StockService.get_total_stock_value(self.restaurant)
        self.assertEqual(value, Decimal("6000.00"))

    def test_get_stock_history(self):
        StockService.manual_stock_adjustment(
            self.item, Decimal("10"), StockEntry.EntryType.MANUAL_ADD.value,
            self.restaurant,
        )
        history = StockService.get_stock_history(self.item, self.restaurant)
        self.assertEqual(history.count(), 1)


class PurchaseServiceTest(PurchaseTestBase):

    def setUp(self):
        super().setUp()
        self.vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Main Supplier"
        )
        self.item = InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Flour",
            unit=InventoryItem.Unit.KG.value,
            current_stock=Decimal("0"),
            cost_per_unit=Decimal("50.00"),
        )

    def _create_draft_po(self):
        po = PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            order_number="PO-TEST-001",
            order_date=date.today(),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            inventory_item=self.item,
            item_name=self.item.name,
            unit=self.item.unit,
            quantity=Decimal("100.000"),
            unit_price=Decimal("50.00"),
            amount=Decimal("5000.00"),
        )
        PurchaseService.recalculate_order_totals(po)
        po.refresh_from_db()
        return po

    def test_generate_po_number(self):
        po_num = PurchaseService.generate_po_number(self.restaurant)
        self.assertTrue(po_num.startswith("PO-"))

    def test_approve_order(self):
        po = self._create_draft_po()
        PurchaseService.approve_order(po, self.owner_user)
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.APPROVED.value)

    def test_approve_requires_draft(self):
        po = self._create_draft_po()
        po.status = PurchaseOrder.Status.RECEIVED.value
        po.save()
        with self.assertRaises(ValueError):
            PurchaseService.approve_order(po, self.owner_user)

    def test_approve_requires_items(self):
        po = PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            order_number="PO-EMPTY",
            order_date=date.today(),
        )
        with self.assertRaises(ValueError):
            PurchaseService.approve_order(po, self.owner_user)

    def test_receive_order(self):
        po = self._create_draft_po()
        PurchaseService.approve_order(po, self.owner_user)
        PurchaseService.receive_order(po, self.owner_user)
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.RECEIVED.value)

    def test_receive_with_auto_invoice(self):
        po = self._create_draft_po()
        PurchaseService.approve_order(po, self.owner_user)
        invoice = PurchaseService.receive_order(
            po, self.owner_user, auto_create_invoice=True
        )
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.vendor, self.vendor)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("100.000"))

    def test_cancel_order(self):
        po = self._create_draft_po()
        PurchaseService.cancel_order(po, self.owner_user)
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.CANCELLED.value)

    def test_cancel_received_order_fails(self):
        po = self._create_draft_po()
        po.status = PurchaseOrder.Status.RECEIVED.value
        po.save()
        with self.assertRaises(ValueError):
            PurchaseService.cancel_order(po, self.owner_user)

    def test_recalculate_order_totals(self):
        po = self._create_draft_po()
        self.assertEqual(po.total_amount, Decimal("5000.00"))


class PaymentServiceTest(PurchaseTestBase):

    def setUp(self):
        super().setUp()
        self.vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Payment Vendor"
        )
        self.customer = Customer.objects.create(
            restaurant=self.restaurant,
            name="Credit Customer",
            phone="5555555555",
            opening_balance=Decimal("10000.00"),
        )

    def test_record_vendor_payment(self):
        invoice = PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            invoice_number="INV-PAY-001",
            invoice_date=date.today(),
            total_amount=Decimal("5000.00"),
        )
        payment = PaymentService.record_vendor_payment(
            restaurant=self.restaurant,
            vendor=self.vendor,
            amount=Decimal("3000.00"),
            payment_mode="CASH",
            payment_date=date.today(),
            purchase_invoice=invoice,
            user=self.owner_user,
        )
        self.assertEqual(payment.amount, Decimal("3000.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("3000.00"))
        self.assertEqual(
            invoice.status, PurchaseInvoice.Status.PARTIALLY_PAID.value
        )

    def test_full_payment_marks_paid(self):
        invoice = PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            invoice_number="INV-PAY-002",
            invoice_date=date.today(),
            total_amount=Decimal("2000.00"),
        )
        PaymentService.record_vendor_payment(
            restaurant=self.restaurant,
            vendor=self.vendor,
            amount=Decimal("2000.00"),
            payment_mode="UPI",
            payment_date=date.today(),
            purchase_invoice=invoice,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PurchaseInvoice.Status.PAID.value)

    def test_vendor_outstanding(self):
        PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            invoice_number="INV-OUT-001",
            invoice_date=date.today(),
            total_amount=Decimal("5000.00"),
            amount_paid=Decimal("1000.00"),
            status=PurchaseInvoice.Status.PARTIALLY_PAID.value,
        )
        outstanding = PaymentService.get_vendor_outstanding(
            self.vendor, self.restaurant
        )
        self.assertEqual(outstanding, Decimal("4000.00"))

    def test_customer_outstanding(self):
        outstanding = PaymentService.get_customer_outstanding(
            self.customer, self.restaurant
        )
        self.assertEqual(outstanding, Decimal("10000.00"))

    def test_customer_outstanding_after_payment(self):
        PaymentService.record_customer_payment(
            restaurant=self.restaurant,
            customer=self.customer,
            amount=Decimal("3000.00"),
            payment_mode="CASH",
            payment_date=date.today(),
        )
        outstanding = PaymentService.get_customer_outstanding(
            self.customer, self.restaurant
        )
        self.assertEqual(outstanding, Decimal("7000.00"))

    def test_total_accounts_payable(self):
        PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            invoice_number="INV-AP-001",
            invoice_date=date.today(),
            total_amount=Decimal("3000.00"),
            amount_paid=Decimal("0"),
        )
        PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=self.vendor,
            invoice_number="INV-AP-002",
            invoice_date=date.today(),
            total_amount=Decimal("2000.00"),
            amount_paid=Decimal("500.00"),
            status=PurchaseInvoice.Status.PARTIALLY_PAID.value,
        )
        total = PaymentService.get_total_accounts_payable(self.restaurant)
        self.assertEqual(total, Decimal("4500.00"))


class FinanceSummaryServiceTest(PurchaseTestBase):

    def test_dashboard_summary_structure(self):
        summary = FinanceSummaryService.get_dashboard_summary(self.restaurant)
        self.assertIn("total_accounts_payable", summary)
        self.assertIn("total_accounts_receivable", summary)
        self.assertIn("total_stock_value", summary)
        self.assertIn("low_stock_items_count", summary)
        self.assertIn("pending_purchase_orders_count", summary)
        self.assertIn("unpaid_invoices_count", summary)
        self.assertIn("total_expenses_this_month", summary)
        self.assertIn("expenses_by_category", summary)

    def test_dashboard_with_data(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Summary Vendor"
        )
        PurchaseInvoice.objects.create(
            restaurant=self.restaurant,
            vendor=vendor,
            invoice_number="INV-SUM-001",
            invoice_date=date.today(),
            total_amount=Decimal("5000.00"),
        )
        InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Summary Item",
            current_stock=Decimal("10.000"),
            cost_per_unit=Decimal("100.00"),
            low_stock_threshold=Decimal("20.000"),
        )
        summary = FinanceSummaryService.get_dashboard_summary(self.restaurant)
        self.assertEqual(summary["total_accounts_payable"], Decimal("5000.00"))
        self.assertEqual(summary["total_stock_value"], Decimal("1000.00"))
        self.assertEqual(summary["low_stock_items_count"], 1)
        self.assertEqual(summary["unpaid_invoices_count"], 1)


# ──────────────────────────────────────────────
# API TESTS
# ──────────────────────────────────────────────


class VendorAPITest(PurchaseTestBase):

    def test_list_vendors_as_manager(self):
        Vendor.objects.create(restaurant=self.restaurant, name="API Vendor")
        self.client.login(username="manager", password="testpass123")
        response = self.client.get("/purchase/api/vendors/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_create_vendor(self):
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/vendors/",
            {"name": "New Vendor", "phone": "1111111111"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "New Vendor")

    def test_create_duplicate_vendor_fails(self):
        Vendor.objects.create(restaurant=self.restaurant, name="Dup Vendor")
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/vendors/",
            {"name": "Dup Vendor"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_waiter_cannot_access_vendors(self):
        self.client.login(username="waiter", password="testpass123")
        response = self.client.get("/purchase/api/vendors/")
        self.assertEqual(response.status_code, 403)

    def test_delete_vendor_requires_owner(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Delete Me"
        )
        self.client.login(username="manager", password="testpass123")
        response = self.client.delete(f"/purchase/api/vendors/{vendor.id}")
        self.assertEqual(response.status_code, 403)

        self.client.login(username="owner", password="testpass123")
        response = self.client.delete(f"/purchase/api/vendors/{vendor.id}")
        self.assertEqual(response.status_code, 200)


class CustomerAPITest(PurchaseTestBase):

    def test_list_customers_as_waiter(self):
        Customer.objects.create(
            restaurant=self.restaurant, name="Cust", phone="1234"
        )
        self.client.login(username="waiter", password="testpass123")
        response = self.client.get("/purchase/api/customers/")
        self.assertEqual(response.status_code, 200)

    def test_create_customer_requires_manager(self):
        self.client.login(username="waiter", password="testpass123")
        response = self.client.post(
            "/purchase/api/customers/",
            {"name": "Test", "phone": "9999"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/customers/",
            {"name": "Test", "phone": "9999"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_customer_outstanding_endpoint(self):
        customer = Customer.objects.create(
            restaurant=self.restaurant,
            name="Credit Cust",
            phone="7777",
            opening_balance=Decimal("5000.00"),
        )
        self.client.login(username="manager", password="testpass123")
        response = self.client.get(
            f"/purchase/api/customers/{customer.id}/outstanding/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Decimal(response.json()["outstanding_balance"]), Decimal("5000.00")
        )


class InventoryAPITest(PurchaseTestBase):

    def test_list_inventory(self):
        InventoryItem.objects.create(
            restaurant=self.restaurant, name="Test Item"
        )
        self.client.login(username="waiter", password="testpass123")
        response = self.client.get("/purchase/api/inventory/")
        self.assertEqual(response.status_code, 200)

    def test_low_stock_endpoint(self):
        InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Low Item",
            current_stock=Decimal("1.000"),
            low_stock_threshold=Decimal("10.000"),
        )
        self.client.login(username="manager", password="testpass123")
        response = self.client.get("/purchase/api/inventory/low-stock/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_stock_entry(self):
        item = InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="Stock Item",
            current_stock=Decimal("50.000"),
        )
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            f"/purchase/api/inventory/{item.id}/stock-entry/",
            {
                "entry_type": "MANUAL_ADD",
                "quantity": "25.000",
                "notes": "Restocked",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        item.refresh_from_db()
        self.assertEqual(item.current_stock, Decimal("75.000"))


class ExpenseAPITest(PurchaseTestBase):

    def test_create_expense_category(self):
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/expense-categories/",
            {"name": "Utilities"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_create_expense(self):
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/expenses/",
            {
                "description": "Electricity bill",
                "amount": "2500.00",
                "expense_date": str(date.today()),
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)


class DashboardAPITest(PurchaseTestBase):

    def test_dashboard_endpoint(self):
        self.client.login(username="manager", password="testpass123")
        response = self.client.get("/purchase/api/dashboard/summary/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_accounts_payable", data)
        self.assertIn("total_stock_value", data)


class PurchaseOrderAPITest(PurchaseTestBase):

    def setUp(self):
        super().setUp()
        self.vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="PO Vendor"
        )
        self.item = InventoryItem.objects.create(
            restaurant=self.restaurant,
            name="PO Item",
            unit=InventoryItem.Unit.KG.value,
        )

    def test_create_purchase_order(self):
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/purchase-orders/",
            {
                "vendor_id": str(self.vendor.id),
                "order_date": str(date.today()),
                "items": [
                    {
                        "inventory_item_id": str(self.item.id),
                        "quantity": "10.000",
                        "unit_price": "100.00",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "DRAFT")
        self.assertGreater(Decimal(data["total_amount"]), 0)

    def test_approve_and_receive_flow(self):
        self.client.login(username="manager", password="testpass123")
        # Create
        response = self.client.post(
            "/purchase/api/purchase-orders/",
            {
                "vendor_id": str(self.vendor.id),
                "order_date": str(date.today()),
                "items": [
                    {
                        "inventory_item_id": str(self.item.id),
                        "quantity": "5.000",
                        "unit_price": "200.00",
                    }
                ],
            },
            content_type="application/json",
        )
        po_id = response.json()["id"]

        # Approve
        response = self.client.post(
            f"/purchase/api/purchase-orders/{po_id}/approve/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "APPROVED")

        # Receive with auto invoice
        response = self.client.post(
            f"/purchase/api/purchase-orders/{po_id}/receive/",
            {"auto_create_invoice": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "RECEIVED")

        # Verify stock was updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("5.000"))


class PaymentAPITest(PurchaseTestBase):

    def test_create_vendor_payment(self):
        vendor = Vendor.objects.create(
            restaurant=self.restaurant, name="Pay Vendor"
        )
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/payments/",
            {
                "payment_type": "VENDOR_PAYMENT",
                "vendor_id": str(vendor.id),
                "amount": "1500.00",
                "payment_mode": "CASH",
                "payment_date": str(date.today()),
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_create_customer_receipt(self):
        customer = Customer.objects.create(
            restaurant=self.restaurant,
            name="Pay Customer",
            phone="3333",
            opening_balance=Decimal("5000.00"),
        )
        self.client.login(username="manager", password="testpass123")
        response = self.client.post(
            "/purchase/api/payments/",
            {
                "payment_type": "CUSTOMER_RECEIPT",
                "customer_id": str(customer.id),
                "amount": "2000.00",
                "payment_mode": "UPI",
                "payment_date": str(date.today()),
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
