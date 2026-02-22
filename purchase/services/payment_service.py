from decimal import Decimal
from django.db import transaction, models
from purchase.models.payment import Payment
from purchase.models.purchase_invoice import PurchaseInvoice


class PaymentService:

    @classmethod
    @transaction.atomic
    def record_vendor_payment(
        cls,
        restaurant,
        vendor,
        amount,
        payment_mode,
        payment_date,
        purchase_invoice=None,
        reference_number=None,
        notes=None,
        user=None,
    ):
        """
        Record a payment to a vendor.
        If linked to an invoice, update invoice.amount_paid and status.
        """
        payment = Payment.objects.create(
            restaurant=restaurant,
            payment_type=Payment.PaymentType.VENDOR_PAYMENT.value,
            payment_mode=payment_mode,
            vendor=vendor,
            purchase_invoice=purchase_invoice,
            amount=amount,
            payment_date=payment_date,
            reference_number=reference_number,
            notes=notes,
            updated_by=user,
        )

        if purchase_invoice:
            invoice = PurchaseInvoice.objects.select_for_update().get(
                id=purchase_invoice.id
            )
            invoice.amount_paid += Decimal(str(amount))
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = PurchaseInvoice.Status.PAID.value
            else:
                invoice.status = PurchaseInvoice.Status.PARTIALLY_PAID.value
            invoice.save(update_fields=["amount_paid", "status", "updated_at"])

        return payment

    @classmethod
    def record_customer_payment(
        cls,
        restaurant,
        customer,
        amount,
        payment_mode,
        payment_date,
        reference_number=None,
        notes=None,
        user=None,
    ):
        """Record a payment received from a customer."""
        payment = Payment.objects.create(
            restaurant=restaurant,
            payment_type=Payment.PaymentType.CUSTOMER_RECEIPT.value,
            payment_mode=payment_mode,
            customer=customer,
            amount=amount,
            payment_date=payment_date,
            reference_number=reference_number,
            notes=notes,
            updated_by=user,
        )
        return payment

    @classmethod
    def get_vendor_outstanding(cls, vendor, restaurant):
        """
        Total amount owed to vendor:
        Sum of balance_due across PENDING/PARTIALLY_PAID invoices.
        """
        result = PurchaseInvoice.objects.filter(
            vendor=vendor,
            restaurant=restaurant,
            is_deleted=False,
            status__in=[
                PurchaseInvoice.Status.PENDING.value,
                PurchaseInvoice.Status.PARTIALLY_PAID.value,
            ],
        ).aggregate(
            total=models.Sum(
                models.F("total_amount") - models.F("amount_paid"),
                output_field=models.DecimalField(),
            )
        )
        return result["total"] or Decimal("0.00")

    @classmethod
    def get_customer_outstanding(cls, customer, restaurant):
        """
        Outstanding balance for a customer:
        opening_balance + total unpaid bills - total received payments.
        """
        from sale.models.bill import Bill

        total_received = Payment.objects.filter(
            customer=customer,
            restaurant=restaurant,
            is_deleted=False,
            payment_type=Payment.PaymentType.CUSTOMER_RECEIPT.value,
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        # Sum of unpaid completed bills linked to this customer
        total_billed = Bill.objects.filter(
            customer=customer,
            restaurant=restaurant,
            is_deleted=False,
            active=False,
            payment_status=Bill.PaymentStatus.UNPAID.value,
        ).aggregate(total=models.Sum("amount"))["total"] or 0
        total_billed = Decimal(str(total_billed))

        return customer.opening_balance + total_billed - total_received

    @classmethod
    def get_total_accounts_payable(cls, restaurant):
        """Sum of all vendor outstanding amounts."""
        result = PurchaseInvoice.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            status__in=[
                PurchaseInvoice.Status.PENDING.value,
                PurchaseInvoice.Status.PARTIALLY_PAID.value,
            ],
        ).aggregate(
            total=models.Sum(
                models.F("total_amount") - models.F("amount_paid"),
                output_field=models.DecimalField(),
            )
        )
        return result["total"] or Decimal("0.00")

    @classmethod
    def get_total_accounts_receivable(cls, restaurant):
        """Sum of all customer outstanding amounts."""
        from purchase.models.customer import Customer
        from sale.models.bill import Bill

        customers = list(Customer.get_customers_for_restaurant(restaurant))
        if not customers:
            return Decimal("0.00")

        # Batch query: total received payments per customer (1 query)
        payment_totals = dict(
            Payment.objects.filter(
                restaurant=restaurant,
                is_deleted=False,
                payment_type=Payment.PaymentType.CUSTOMER_RECEIPT.value,
                customer__in=customers,
            ).values('customer_id').annotate(
                total=models.Sum('amount')
            ).values_list('customer_id', 'total')
        )

        # Batch query: total unpaid bills per customer (1 query)
        bill_totals = dict(
            Bill.objects.filter(
                restaurant=restaurant,
                is_deleted=False,
                active=False,
                payment_status=Bill.PaymentStatus.UNPAID.value,
                customer__in=customers,
            ).values('customer_id').annotate(
                total=models.Sum('amount')
            ).values_list('customer_id', 'total')
        )

        # Sum outstanding in Python (no DB hits)
        total = Decimal("0.00")
        for customer in customers:
            total_received = payment_totals.get(customer.id, Decimal("0.00"))
            total_billed = Decimal(str(bill_totals.get(customer.id, 0)))
            outstanding = customer.opening_balance + total_billed - total_received
            if outstanding > 0:
                total += outstanding
        return total
