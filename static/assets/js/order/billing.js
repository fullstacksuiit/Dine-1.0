window.DinePay = window.DinePay || {};

DinePay.BillingMixin = {
  data: function () {
    return {
      showBillingModal: false,
      billingMode: 'create',
      editingBillId: null,
      pendingChanges: [],
      isProcessingChanges: false,
      loyaltyInfo: null,
      loyaltyCheckTimeout: null,
      billing: {
        customerName: '',
        contact: '',
        customerGstin: '',
        orderType: 'RESTAURANT',
        paymentType: 'CASH',
        items: [],
        subtotal: 0,
        discount: 0,
        discountPercent: 0,
        net: 0,
        cgst: 0,
        sgst: 0,
        igst: 0,
        cgstPercent: 2.5,
        sgstPercent: 2.5,
        igstPercent: 0,
        deliveryCharge: 0,
        packagingCharge: 0,
        total: 0,
        loyaltyInfo: null,
        loyaltyCheckTimeout: null
      }
    };
  },

  methods: {
    resetBilling() {
      this.pendingChanges = [];
      this.isProcessingChanges = false;

      var initialCgstPercent = this.restaurantHasGstin ? 2.5 : 0;
      var initialSgstPercent = this.restaurantHasGstin ? 2.5 : 0;

      this.billing = {
        customerName: '',
        contact: '',
        customerGstin: '',
        orderType: 'RESTAURANT',
        paymentType: 'CASH',
        items: [],
        subtotal: 0,
        discount: 0,
        discountPercent: 0,
        net: 0,
        cgst: 0,
        sgst: 0,
        igst: 0,
        cgstPercent: initialCgstPercent,
        sgstPercent: initialSgstPercent,
        igstPercent: 0,
        deliveryCharge: 0,
        packagingCharge: 0,
        total: 0,
        loyaltyInfo: null,
        loyaltyCheckTimeout: null
      };
    },

    calculateBilling() {
      var subtotal = 0;

      if (this.orderType === 'takeaway') {
        subtotal = this.currentOrder
          .filter(function (item) { return item.name.trim() && item.id && item.price; })
          .reduce(function (total, item) { return total + (item.price * item.quantity); }, 0);
      } else {
        subtotal = this.billing.items.reduce(function (total, item) { return total + item.amount; }, 0);
      }

      this.billing.subtotal = subtotal;
      this.billing.discount = parseFloat(((this.billing.subtotal * this.billing.discountPercent) / 100).toFixed(2));
      this.billing.net = this.billing.subtotal - this.billing.discount;

      if (!this.restaurantHasGstin) {
        this.billing.cgst = 0;
        this.billing.sgst = 0;
        this.billing.igst = 0;
      } else {
        this.billing.cgst = parseFloat(((this.billing.cgstPercent / 100) * this.billing.net).toFixed(2));
        this.billing.sgst = parseFloat(((this.billing.sgstPercent / 100) * this.billing.net).toFixed(2));
        this.billing.igst = parseFloat(((this.billing.igstPercent / 100) * this.billing.net).toFixed(2));
      }

      var totalTax = this.billing.cgst + this.billing.sgst + this.billing.igst;
      var delivery = parseFloat(this.billing.deliveryCharge) || 0;
      var packaging = parseFloat(this.billing.packagingCharge) || 0;

      this.billing.total = Math.round(this.billing.net + totalTax + delivery + packaging);
    },

    calculateDiscountPercent() {
      if (this.billing.subtotal > 0) {
        this.billing.discountPercent = (this.billing.discount / this.billing.subtotal) * 100;
      }
      this.calculateBilling();
    },

    onCgstSgstPercentChange() {
      if (!this.restaurantHasGstin) {
        this.billing.cgstPercent = 0;
        this.billing.sgstPercent = 0;
        this.billing.igstPercent = 0;
        this.calculateBilling();
        return;
      }
      this.billing.sgstPercent = this.billing.cgstPercent;
      this.billing.igstPercent = 0;
      this.calculateBilling();
    },

    onBillingIgstPercentChange() {
      if (!this.restaurantHasGstin) {
        this.billing.cgstPercent = 0;
        this.billing.sgstPercent = 0;
        this.billing.igstPercent = 0;
        this.calculateBilling();
        return;
      }
      if (this.billing.igstPercent > 0) {
        this.billing.cgstPercent = 0;
        this.billing.sgstPercent = 0;
      }
      this.calculateBilling();
    },

    updateBillingOrderType() {
      var self = this;
      if (this.orderType === 'takeaway') {
        this.currentOrder.forEach(function (item) {
          if (item.id) {
            var dish = self.dishes.find(function (d) { return d.id === item.id; });
            if (dish) self.updateItemPrice(item, dish);
          }
        });
      }
      if (this.orderType !== 'takeaway' && Array.isArray(this.billing.items)) {
        this.billing.items.forEach(function (item) {
          if (item.dish_id) {
            var dish = self.dishes.find(function (d) { return d.id === item.dish_id; });
            if (dish) {
              self.updateItemPrice(item, dish);
              item.rate = item.price;
              item.amount = item.rate * item.quantity;
            }
          }
        });
      }

      if (this.billing.orderType === 'ZOMATO' || !this.restaurantHasGstin) {
        this.billing.cgstPercent = 0;
        this.billing.sgstPercent = 0;
        this.billing.igstPercent = 0;
      } else {
        this.billing.cgstPercent = 2.5;
        this.billing.sgstPercent = 2.5;
        this.billing.igstPercent = 0;
      }

      this.calculateBilling();
    },

    onPaymentTypeChange() {
      if (this.billing.paymentType === 'Non Paid') {
        this.billing.customerName = this.billing.orderType;
      }
    },

    checkCustomerLoyalty(contactField) {
      contactField = contactField || 'contact';
      var self = this;
      var contact = contactField === 'billing' ? this.billing.contact : this[contactField];

      if (contactField === 'billing' && this.billing.loyaltyCheckTimeout) {
        clearTimeout(this.billing.loyaltyCheckTimeout);
      } else if (this.loyaltyCheckTimeout) {
        clearTimeout(this.loyaltyCheckTimeout);
      }

      if (!contact || contact.length < 6) {
        if (contactField === 'billing') { this.billing.loyaltyInfo = null; }
        else { this.loyaltyInfo = null; }
        return;
      }

      var timeout = setTimeout(function () {
        axios.get(self.base_url + '/sale/api/customer-loyalty/?contact=' + encodeURIComponent(contact))
          .then(function (response) {
            var loyaltyData = response.data;
            if (loyaltyData && loyaltyData.total_spent) {
              loyaltyData.total_spent_formatted = self.formatCurrency(loyaltyData.total_spent);
            }
            if (contactField === 'billing') {
              self.billing.loyaltyInfo = loyaltyData;
              if (loyaltyData.recommended_discount > 0 && self.billing.discountPercent === 0) {
                self.billing.discountPercent = loyaltyData.recommended_discount;
                self.calculateBilling();
              }
            } else {
              self.loyaltyInfo = loyaltyData;
            }
          })
          .catch(function (error) {
            console.error('Error fetching loyalty info:', error);
            if (contactField === 'billing') { self.billing.loyaltyInfo = null; }
            else { self.loyaltyInfo = null; }
          });
      }, 800);

      if (contactField === 'billing') { this.billing.loyaltyCheckTimeout = timeout; }
      else { this.loyaltyCheckTimeout = timeout; }
    },

    // Billing modal methods
    openBillingModal() {
      this.billingMode = 'create';
      this.editingBillId = null;
      this.initializeBilling();
      this.showBillingModal = true;
    },

    closeBillingModal() {
      this.showBillingModal = false;
      this.billingMode = 'create';
      this.editingBillId = null;
      this.resetBilling();
    },

    closeBillingModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeBillingModal();
    },

    checkBillingCustomerLoyalty() {
      this.checkCustomerLoyalty('billing');
    },

    async initializeBilling() {
      try {
        var billData;
        if (this.billingMode === 'edit' && this.editingBillId) {
          var response = await axios.get(this.base_url + '/sale/api/bills/' + encodeURIComponent(this.editingBillId) + '?group=false');
          billData = response.data;
        } else {
          var response2 = await axios.get(this.base_url + '/sale/api/bills/' + encodeURIComponent(this.currentTableId) + '?group=false');
          billData = response2.data;
        }

        this.resetBilling();

        this.billing.customerName = (billData.bill_details && billData.bill_details.customer_name) || '';
        this.billing.contact = (billData.bill_details && billData.bill_details.contact) || '';
        this.billing.customerGstin = (billData.bill_details && billData.bill_details.customer_gstin) || '';
        this.billing.orderType = (billData.bill_details && billData.bill_details.order_type) || 'RESTAURANT';

        var paymentType = billData.bill_details && billData.bill_details.payment_type;
        this.billing.paymentType = (paymentType && paymentType !== 'undefined') ? paymentType.toUpperCase() : 'CASH';

        this.billing.items = [];
        var self = this;
        if (billData.orders && billData.orders.length > 0) {
          billData.orders.forEach(function (order) {
            var item = {
              id: order.id,
              name: order.dish.name,
              quantity: order.quantity,
              size: order.size,
              rate: 0,
              amount: 0,
              dish_id: order.dish.id
            };

            if (self.billing.orderType === 'RESTAURANT') {
              item.rate = item.size === 'full' ? order.dish.restaurant_full_price : order.dish.restaurant_half_price;
            } else if (self.billing.orderType === 'SWIGGY') {
              item.rate = item.size === 'full' ? order.dish.swiggy_full_price : order.dish.swiggy_half_price;
            } else if (self.billing.orderType === 'ZOMATO') {
              item.rate = item.size === 'full' ? order.dish.zomato_full_price : order.dish.zomato_half_price;
            }

            item.amount = item.rate * item.quantity;
            self.billing.items.push(item);
          });
        }

        if (billData.bill_details && billData.bill_details.active === false) {
          this.billing.discount = billData.bill_details.discount || 0;
          this.billing.discountPercent = billData.bill_details.sub_total ?
            ((this.billing.discount / billData.bill_details.sub_total) * 100) : 0;
          this.billing.deliveryCharge = billData.bill_details.delivery_charge || 0;
          this.billing.packagingCharge = billData.bill_details.packaging_charge || 0;
          this.billing.cgst = billData.bill_details.cgst || 0;
          this.billing.sgst = billData.bill_details.sgst || 0;
          this.billing.igst = billData.bill_details.igst || 0;
        }

        if (this.billing.contact) this.checkBillingCustomerLoyalty();

        this.calculateBilling();
      } catch (error) {
        console.error('Error initializing billing:', error);
        alert('Error loading bill data. Please try again.');
      }
    },

    async updateBillAPI(billId) {
      var payload = {
        customer_name: this.billing.customerName,
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

      try {
        var response = await axios.put(this.base_url + '/sale/api/bills/' + encodeURIComponent(billId), payload, {
          headers: { 'X-CSRFToken': this.getCsrfToken() }
        });
        if (response.status >= 200 && response.status < 300) {
          return { success: true, data: response.data };
        } else {
          throw new Error('Server returned status ' + response.status);
        }
      } catch (error) {
        console.error('Error updating bill via API:', error);
        return { success: false, error: error.message };
      }
    },

    async saveBill() {
      try {
        if (!this.currentTableId) {
          this.showToast('Error: No table selected. Please try again.', 'error');
          return null;
        }

        if (this.billing.contact && this.billing.contact.trim().length < 6) {
          this.showToast('Contact number must be at least 6 characters long.', 'error');
          return;
        }

        var changeResult = await this.processPendingChanges();
        if (!changeResult.success) {
          this.showToast('Failed to process order changes: ' + changeResult.message, 'error');
          return null;
        }

        var result = await this.updateBillAPI(this.currentTableId);

        if (result.success) {
          this.showToast('Bill saved successfully!', 'success');
          this.closeBillingModal();
          this.closeExistingOrdersModal();
          this.refreshAllOrderTabs();
          return this.currentTableId;
        } else {
          this.showToast('Failed to save bill. Please try again.', 'error');
          return null;
        }
      } catch (error) {
        console.error('Error saving bill:', error);
        this.showToast('Failed to save bill. Please try again.', 'error');
        return null;
      }
    },

    async saveBillAndPrint() {
      try {
        if (!this.currentTableId) {
          this.showToast('Error: No table selected. Please try again.', 'error');
          return;
        }

        if (this.billing.contact && this.billing.contact.trim().length < 6) {
          this.showToast('Contact number must be at least 6 characters long.', 'error');
          return;
        }

        var changeResult = await this.processPendingChanges();
        if (!changeResult.success) {
          this.showToast('Failed to process order changes: ' + changeResult.message, 'error');
          return;
        }

        var result = await this.updateBillAPI(this.currentTableId);

        if (result.success) {
          var url = this.base_url + '/sale/invoice/' + encodeURIComponent(this.currentTableId) + '?print=true';
          window.open(url, '_blank');
          this.closeBillingModal();
          this.closeExistingOrdersModal();
          this.showToast('Bill saved and invoice opened for printing!', 'success');
        } else {
          this.showToast('Failed to save bill. Please try again.', 'error');
        }
      } catch (error) {
        console.error('Error in saveBillAndPrint:', error);
        this.showToast('Failed to save and print bill. Please try again.', 'error');
      }
    },

    async updateBill() {
      try {
        if (!this.editingBillId) {
          alert('Error: No bill selected for editing. Please try again.');
          return;
        }

        if (this.billing.contact && this.billing.contact.trim().length < 6) {
          alert('Contact number must be at least 6 characters long.');
          return;
        }

        var changeResult = await this.processPendingChanges();
        if (!changeResult.success) {
          alert('Failed to process order changes: ' + changeResult.message);
          return;
        }

        var result = await this.updateBillAPI(this.editingBillId);

        if (result.success) {
          alert('Bill updated successfully!');
          this.closeBillingModal();
          this.refreshAllOrderTabs();
        } else {
          alert('Failed to update bill. Please try again.');
        }
      } catch (error) {
        console.error('Error updating bill:', error);
        alert('Failed to update bill. Please try again.');
      }
    },

    // Order editing methods for billing modal
    async editBillingOrderQuantity(orderId, newQuantity) {
      if (!orderId || !newQuantity || newQuantity <= 0) {
        this.showToast('Invalid quantity. Please enter a positive number.', 'error');
        return;
      }

      this.addPendingChange({
        type: 'quantity',
        orderId: orderId,
        newQuantity: parseInt(newQuantity),
        originalQuantity: this.getOrderQuantityById(orderId)
      });

      this.updateLocalBillingItem(orderId, 'quantity', parseInt(newQuantity));
    },

    async removeBillingOrder(orderId, dishName) {
      if (!confirm('Are you sure you want to remove "' + dishName + '" from this bill? This cannot be undone.')) return;

      this.addPendingChange({
        type: 'remove',
        orderId: orderId,
        dishName: dishName
      });

      this.removeLocalBillingItem(orderId);
    },

    addPendingChange(change) {
      this.pendingChanges = this.pendingChanges.filter(function (c) { return c.orderId !== change.orderId; });
      this.pendingChanges.push(Object.assign({}, change, { timestamp: Date.now() }));
    },

    getOrderQuantityById(orderId) {
      var item = this.billing.items.find(function (i) { return i.id === orderId; });
      return item ? item.quantity : 0;
    },

    updateLocalBillingItem(orderId, field, value) {
      var item = this.billing.items.find(function (i) { return i.id === orderId; });
      if (item) {
        if (field === 'quantity') {
          item.quantity = value;
          item.amount = item.rate * item.quantity;
        }
        this.calculateBilling();
      }
    },

    removeLocalBillingItem(orderId) {
      this.billing.items = this.billing.items.filter(function (i) { return i.id !== orderId; });
      this.calculateBilling();
    },

    async processPendingChanges() {
      if (this.pendingChanges.length === 0) {
        return { success: true, message: 'No pending changes to process' };
      }

      this.isProcessingChanges = true;
      var results = [];
      var self = this;

      try {
        for (var i = 0; i < this.pendingChanges.length; i++) {
          var change = this.pendingChanges[i];
          try {
            if (change.type === 'quantity') {
              await axios.patch(self.base_url + '/sale/api/orders/' + change.orderId, {
                quantity: change.newQuantity
              }, {
                headers: { 'X-CSRFToken': self.getCsrfToken(), 'Content-Type': 'application/json' }
              });
              results.push({ success: true, change: change, message: 'Quantity updated' });
            } else if (change.type === 'remove') {
              await axios.delete(self.base_url + '/sale/api/orders/' + change.orderId, {
                headers: { 'X-CSRFToken': self.getCsrfToken(), 'Content-Type': 'application/json' }
              });
              results.push({ success: true, change: change, message: 'Order removed' });
            }
          } catch (error) {
            console.error('Failed to process change for order ' + change.orderId + ':', error);
            results.push({ success: false, change: change, error: error.message });
          }
        }

        this.pendingChanges = [];

        var failedChanges = results.filter(function (r) { return !r.success; });
        if (failedChanges.length > 0) {
          return { success: false, message: failedChanges.length + ' changes failed to process', results: results };
        }

        return { success: true, message: 'All changes processed successfully', results: results };
      } finally {
        this.isProcessingChanges = false;
      }
    }
  }
};
