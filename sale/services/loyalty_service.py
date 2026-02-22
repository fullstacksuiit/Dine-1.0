from django.db.models import Count, Sum, Avg, Q
from datetime import datetime, timedelta
from sale.models import Bill


class LoyaltyService:
    """
    Service to calculate customer loyalty metrics based on existing bill data.
    Uses contact number as the customer identifier.
    """

    LOYALTY_TIERS = {
        'NEW': {
            'name': 'New Customer',
            'color': '#28a745',  # Green
            'icon': '🆕',
            'description': 'First-time customer'
        },
        'REPEAT': {
            'name': 'Repeat Customer',
            'color': '#17a2b8',  # Blue
            'icon': '🔄',
            'description': '2-5 orders'
        },
        'LOYAL': {
            'name': 'Loyal Customer',
            'color': '#ffc107',  # Gold
            'icon': '⭐',
            'description': '6-15 orders or ₹15,000+ spent'
        },
        'VIP': {
            'name': 'VIP Customer',
            'color': '#6f42c1',  # Purple
            'icon': '👑',
            'description': '15+ orders or ₹30,000+ spent'
        }
    }

    @classmethod
    def get_customer_loyalty_info(cls, contact, restaurant):
        """
        Calculate loyalty tier and metrics for a customer based on contact number.

        Args:
            contact (str): Customer's contact number
            restaurant: Restaurant instance

        Returns:
            dict: Customer loyalty information including tier, stats, and recommendations
        """
        if not contact or len(contact.strip()) < 6:
            return {
                'tier': 'NEW',
                'tier_info': cls.LOYALTY_TIERS['NEW'],
                'total_orders': 0,
                'total_spent': 0,
                'avg_order_value': 0,
                'last_visit': None,
                'days_since_last_visit': None,
                'is_new': True,
                'recommended_discount': 0
            }

        # Get all bills for this customer at this restaurant
        # Note: Including both active and inactive bills for loyalty calculation
        customer_bills = Bill.get_bills_for_customer(contact, restaurant)

        # Calculate basic metrics
        total_orders = customer_bills.count()
        sale = customer_bills.aggregate(Avg("amount"), Sum("amount"))
        total_spent = round(sale['amount__sum']) or 0
        avg_order_value = round(sale['amount__avg'] or 0)

        # Get last visit information
        last_bill = customer_bills.order_by('-created_at').first()
        last_visit = last_bill.created_at if last_bill else None
        days_since_last_visit = None

        if last_visit:
            # It can sometimes be buggy(due to timezone differences) but given we are calculating based on date, it should be fine for most cases.
            days_since_last_visit = (datetime.now().date() - last_visit.date()).days

        # Determine loyalty tier
        tier = cls._calculate_tier(total_orders, total_spent)

        # Calculate recommended discount based on tier and recency
        recommended_discount = cls._calculate_recommended_discount(
            tier, days_since_last_visit, total_spent
        )

        return {
            'tier': tier,
            'tier_info': cls.LOYALTY_TIERS[tier],
            'total_orders': total_orders,
            'total_spent': float(total_spent),
            'avg_order_value': float(avg_order_value),
            'last_visit': last_visit,
            'days_since_last_visit': days_since_last_visit,
            'is_new': total_orders == 0,
            'recommended_discount': recommended_discount,
        }

    @classmethod
    def _calculate_tier(cls, total_orders, total_spent):
        """Calculate customer tier based on orders and spending."""
        if total_orders == 0:
            return 'NEW'
        elif total_orders >= 15 or total_spent >= 30000:
            return 'VIP'
        elif total_orders >= 6 or total_spent >= 15000:
            return 'LOYAL'
        elif total_orders >= 2:
            return 'REPEAT'
        else:
            return 'NEW'

    @classmethod
    def _calculate_recommended_discount(cls, tier, days_since_last_visit, total_spent):
        """Calculate recommended discount percentage based on loyalty and recency."""
        base_discounts = {
            'NEW': 0,      # Welcome discount for new customers
            'REPEAT': 3,   # Small appreciation discount
            'LOYAL': 5,    # Regular loyalty discount
            'VIP': 10      # Premium discount for VIPs
        }

        discount = base_discounts.get(tier, 0)

        # Cap discount at reasonable limits
        return min(discount, 15)

    @classmethod
    def get_restaurant_loyalty_summary(cls, restaurant, days=30):
        """
        Get loyalty summary for the restaurant.

        Args:
            restaurant: Restaurant instance
            days (int): Number of days to look back

        Returns:
            dict: Summary of customer loyalty metrics
        """
        since_date = datetime.now().date() - timedelta(days=days)

        # Single query: get lifetime stats for all customers who have recent bills
        # Uses conditional aggregation to check for recent activity in the same query
        all_stats = Bill.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            active=False,
            contact__isnull=False,
        ).exclude(contact='').values('contact').annotate(
            total_orders=Count('id'),
            total_spent=Sum('amount'),
            has_recent=Count('id', filter=Q(created_at__gte=since_date)),
        ).filter(has_recent__gt=0)

        # Classify tiers in Python (fast, no DB hits)
        tier_counts = {'NEW': 0, 'REPEAT': 0, 'LOYAL': 0, 'VIP': 0}
        unique_customers = 0

        for stats in all_stats:
            unique_customers += 1
            tier = cls._calculate_tier(stats['total_orders'], stats['total_spent'] or 0)
            tier_counts[tier] += 1

        return {
            'unique_customers': unique_customers,
            'tier_distribution': tier_counts,
            'period_days': days
        }
