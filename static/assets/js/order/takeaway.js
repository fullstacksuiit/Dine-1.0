window.DinePay = window.DinePay || {};

DinePay.TakeawayMixin = {
  data: function () {
    return {
      activeTakeawayOrders: []
    };
  },

  methods: {
    async fetchActiveTakeawayOrders() {
      try {
        if (this.isCacheValid('activeTakeawayOrders')) {
          this.activeTakeawayOrders = this.getCache('activeTakeawayOrders');
          var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeTakeawayOrders'; });
          if (tab) tab.count = this.activeTakeawayOrders.length;
          return;
        }

        var response = await axios.get(this.base_url + '/sale/api/kots/?filter=takeaway', {
          headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' }
        });

        if (response.data.pending_kots !== undefined && response.data.accepted_kots !== undefined) {
          this.activeTakeawayOrders = [].concat(response.data.pending_kots || [], response.data.accepted_kots || []);
        } else {
          this.activeTakeawayOrders = response.data || [];
        }

        this.activeTakeawayOrders.sort(function (a, b) { return new Date(b.created_at) - new Date(a.created_at); });

        this.setCache('activeTakeawayOrders', this.activeTakeawayOrders);

        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeTakeawayOrders'; });
        if (tab) tab.count = this.activeTakeawayOrders.length;

      } catch (error) {
        console.error('Error fetching active takeaway orders:', error);
        this.activeTakeawayOrders = [];
      }
    },

    async updateTakeawayOrderStatus(orderId, newStatus) {
      try {
        var response = await axios.patch(this.base_url + '/sale/api/kots/' + orderId, {
          status: newStatus
        }, {
          headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' }
        });

        if (response.status === 200) {
          this.triggerTakeawayOrderFlow();
        } else {
          this.showToast('Failed to update order status. Please try again.', 'error');
        }
      } catch (error) {
        this.showToast('Failed to update status. Please try again.', 'error');
        this.fetchActiveTakeawayOrders();
      }
    },

    viewTakeawayOrder(orderId) {
      window.open(this.base_url + '/sale/kot/' + orderId, '_blank');
    },

    async saveTakeawayOrderAndBill() {
      if (this.isCreatingOrder) return;
      if (!this.canSendOrder) return;

      this.isCreatingOrder = true;
      try {
        if (this.billing.contact && this.billing.contact.trim().length < 6) {
          throw new Error('Contact number must be at least 6 characters long.');
        }

        var orderData = await this.createOrderAPI();
        if (orderData === null) {
          alert('Error Occurred! Please try again');
          return;
        }
        var billId = orderData.bill_id;

        var billPayload = {
          customer_name: this.billing.customerName || '',
          contact: this.billing.contact,
          customer_gstin: this.billing.customerGstin,
          order_type: this.billing.orderType,
          payment_type: this.billing.paymentType,
          discount: this.billing.discount,
          delivery_charge: this.billing.deliveryCharge,
          packaging_charge: this.billing.packagingCharge,
          sub_total: this.billing.subtotal,
          net: this.billing.net,
          cgst: this.billing.cgst,
          sgst: this.billing.sgst,
          igst: this.billing.igst,
          amount: this.billing.total
        };

        await axios.put(this.base_url + '/sale/api/bills/' + encodeURIComponent(billId), billPayload, {
          headers: { 'X-CSRFToken': this.getCsrfToken() }
        });

        var url = this.base_url + '/sale/invoice/' + encodeURIComponent(billId) + '?print=true';
        window.open(url, '_blank');
        this.triggerTakeawayOrderFlow();
      } catch (error) {
        console.error('Error creating takeaway order and bill:', error);
        if (error.message.includes('Please add at least one valid item') ||
            error.message.includes('Contact number must be at least 6 characters')) {
          alert(error.message);
        } else {
          alert('FAILED TO CREATE TAKEAWAY ORDER. TRY AGAIN.');
        }
      } finally {
        this.isCreatingOrder = false;
      }
    },

    async completeAllTakeawayOrders() {
      if (this.activeTakeawayOrders.length === 0) return;

      alert('Are you sure you want to complete all ' + this.activeTakeawayOrders.length + ' takeaway orders?');

      var nonCompletedOrders = this.activeTakeawayOrders.filter(function (order) {
        return order.status !== 'COMPLETED';
      });
      if (nonCompletedOrders.length === 0) return;

      var self = this;
      var completeAllButton = document.querySelector('.btn-complete-all');
      if (completeAllButton) {
        completeAllButton.textContent = 'Processing...';
        completeAllButton.disabled = true;
      }
      var successCount = 0;
      var failureCount = 0;

      try {
        var completePromises = nonCompletedOrders.map(async function (order) {
          try {
            var response = await axios.patch(self.base_url + '/sale/api/kots/' + order.id, {
              status: 'COMPLETED'
            }, {
              headers: { 'X-CSRFToken': self.getCsrfToken(), 'Content-Type': 'application/json' }
            });

            if (response.status === 200) {
              successCount++;
              return { success: true, order: order };
            } else {
              failureCount++;
              return { success: false, order: order };
            }
          } catch (error) {
            failureCount++;
            return { success: false, order: order, error: error };
          }
        });

        var results = await Promise.all(completePromises);

        results.forEach(function (result) {
          if (result.success) {
            var orderIndex = self.activeTakeawayOrders.findIndex(function (o) { return o.id === result.order.id; });
            if (orderIndex !== -1) self.activeTakeawayOrders[orderIndex].status = 'COMPLETED';
          }
        });

        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeTakeawayOrders'; });
        if (tab) tab.count = this.activeTakeawayOrders.length;

        if (failureCount === 0) {
          this.showToast('Successfully completed all ' + successCount + ' takeaway orders!', 'success');
        } else if (successCount === 0) {
          this.showToast('Failed to complete any orders. Please try again.', 'error');
        } else {
          this.showToast('Completed ' + successCount + ' orders successfully. ' + failureCount + ' failed - please retry those individually.', 'warning');
        }

        this.triggerTakeawayOrderFlow();
      } catch (error) {
        console.error('Error in complete all operation:', error);
        this.showToast('Error. Please try again.', 'error');
      } finally {
        if (completeAllButton) {
          completeAllButton.disabled = false;
          completeAllButton.textContent = '\u2705 Complete All (' + this.activeTakeawayOrders.length + ')';
        }
      }
    },

    // Takeaway shortcut methods
    checkTakeawayCustomerLoyalty() {
      this.checkCustomerLoyalty('billing');
    },

    onTakeawayOrderTypeChange() {
      this.updateBillingOrderType();
    },

    onTakeawayPaymentTypeChange() {
      this.onPaymentTypeChange();
    },

    onTakeawayCgstSgstPercentChange() {
      this.onCgstSgstPercentChange();
    },

    onTakeawayIgstPercentChange() {
      this.onBillingIgstPercentChange();
    },

    calculateTakeawayBill() {
      this.calculateBilling();
    },

    calculateTakeawayDiscountPercent() {
      this.calculateDiscountPercent();
    }
  }
};
