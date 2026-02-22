window.DinePay = window.DinePay || {};

DinePay.OrderPadMixin = {
  data: function () {
    return {
      showOrderModal: false,
      currentTableId: null,
      currentTable: '',
      isEditingTable: false,
      table: '',
      orderType: 'dine',
      lastOrderType: 'dine',
      currentOrder: [],
      contact: '',
      isCreatingOrder: false,
      quantityUpdateTimeout: null
    };
  },

  methods: {
    openNewOrderModal() {
      this.isEditingTable = false;
      this.currentTableId = null;
      this.resetOrderForm();
      this.orderType = this.lastOrderType || 'dine';
      this.showOrderModal = true;
    },

    closeOrderModal() {
      this.showOrderModal = false;
      this.resetOrderForm();
    },

    closeModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeOrderModal();
    },

    resetOrderForm() {
      this.table = '';
      this.contact = '';
      this.loyaltyInfo = null;
      this.orderType = 'dine';
      this.resetOrderItems();
      this.resetBilling();
    },

    resetOrderItems() {
      this.currentOrder = [];
      this.addItem();
    },

    setOrderType(type) {
      this.orderType = type;
      if (type === 'takeaway') {
        this.table = '';
        this.resetBilling();
      }
    },

    // Order item methods
    addItem() {
      this.currentOrder.push({
        name: '',
        quantity: 1,
        size: 'full',
        id: null,
        price: 0,
        notes: '',
        showSuggestions: false,
        suggestions: [],
        selectedSuggestion: 0
      });
    },

    removeItem(index) {
      this.currentOrder.splice(index, 1);
      if (this.currentOrder.length === 0) this.addItem();
    },

    increaseItemQuantity(index) {
      var item = this.currentOrder[index];
      if (item.quantity < 99) item.quantity += 1;
    },

    decreaseItemQuantity(index) {
      var item = this.currentOrder[index];
      if (item.quantity > 1) item.quantity -= 1;
    },

    onSizeChange(index) {
      var item = this.currentOrder[index];
      if (item.id) {
        var dish = this.dishes.find(function (d) { return d.id === item.id; });
        if (dish) this.updateItemPrice(item, dish);
      }
    },

    // Dish search methods
    onItemSearch(index) {
      var item = this.currentOrder[index];
      var input = item.name.trim();
      if (input.length >= 2) {
        this.searchDishes(index, input);
      } else {
        item.showSuggestions = false;
      }
    },

    searchDishes(index, query) {
      var item = this.currentOrder[index];
      var searchTerm = query.toLowerCase();

      function getAbbreviation(name) {
        return name.split(' ').map(function (word) { return word[0]; }).join('').toLowerCase();
      }

      item.suggestions = this.dishes
        .filter(function (dish) {
          var dishName = dish.name.toLowerCase();
          var courseName = (dish.course && dish.course.name) ? dish.course.name.toLowerCase() : '';
          var abbreviation = getAbbreviation(dish.name);
          return dishName.includes(searchTerm) || courseName.includes(searchTerm) || abbreviation.includes(searchTerm);
        })
        .slice(0, 6);

      item.showSuggestions = item.suggestions.length > 0;
      item.selectedSuggestion = 0;
    },

    onItemKeydown(event, index) {
      var item = this.currentOrder[index];
      if (!item.showSuggestions || !item.suggestions.length) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          item.selectedSuggestion = Math.min(item.selectedSuggestion + 1, item.suggestions.length - 1);
          break;
        case 'ArrowUp':
          event.preventDefault();
          item.selectedSuggestion = Math.max(item.selectedSuggestion - 1, 0);
          break;
        case 'Enter':
          event.preventDefault();
          if (item.suggestions[item.selectedSuggestion]) {
            this.selectDish(index, item.suggestions[item.selectedSuggestion]);
          }
          break;
        case 'Escape':
          item.showSuggestions = false;
          break;
      }
    },

    onItemFocus(index) {
      var item = this.currentOrder[index];
      if (item.suggestions.length) item.showSuggestions = true;
    },

    hideItemSuggestions(index) {
      var self = this;
      setTimeout(function () { self.currentOrder[index].showSuggestions = false; }, 150);
    },

    selectDish(index, dish) {
      var item = this.currentOrder[index];
      item.id = dish.id;
      item.name = dish.name;
      item.showSuggestions = false;
      this.updateItemPrice(item, dish);

      if (index === this.currentOrder.length - 1) this.addItem();
    },

    clearOrder() {
      this.resetOrderItems();
    },

    updateItemPrice(item, dish) {
      var orderType = this.orderType === 'takeaway' ? this.takeawayBill.orderType : this.billing.orderType;
      if (orderType === 'RESTAURANT') {
        item.price = item.size.toLowerCase() === 'full' ? dish.restaurant_full_price : dish.restaurant_half_price;
      } else if (orderType === 'SWIGGY') {
        item.price = item.size.toLowerCase() === 'full' ? dish.swiggy_full_price : dish.swiggy_half_price;
      } else if (orderType === 'ZOMATO') {
        item.price = item.size.toLowerCase() === 'full' ? dish.zomato_full_price : dish.zomato_half_price;
      }
      item.price = parseFloat(item.price) || 0;
    },

    // Order submission methods
    async createOrderAPI() {
      var validItems = this.currentOrder.filter(function (item) {
        return item.name.trim() && item.id && item.quantity > 0;
      });

      if (validItems.length === 0) throw new Error('Please add at least one valid item to the order.');

      var payload = {
        table: this.orderType === 'takeaway' ? null : this.table,
        contact: this.orderType === 'takeaway' ? this.billing.contact : this.contact,
        items: validItems.map(function (item) { return item.id; }),
        sizes: validItems.map(function (item) { return item.size; }),
        quantities: validItems.map(function (item) { return item.quantity; }),
        notes: validItems.map(function (item) { return item.notes || ''; }),
        is_takeaway: this.orderType === 'takeaway'
      };

      var response = await axios.post(this.base_url + '/sale/api/orders/', payload, {
        headers: { 'X-CSRFToken': this.getCsrfToken() }
      });

      if (response.status === 201) {
        this.lastOrderType = this.orderType === 'takeaway' ? 'takeaway' : 'dine';
        return response.data;
      }

      return null;
    },

    async sendToKitchen() {
      if (this.isCreatingOrder) return;
      if (!this.canSendOrder) return;

      this.isCreatingOrder = true;
      try {
        var orderData = await this.createOrderAPI();
        if (orderData === null) {
          this.showToast('Error Occured! Please try again', 'error');
          return;
        }
        this.closeOrderModal();
        if (this.orderType === 'takeaway') {
          var invoiceUrl = this.base_url + '/sale/invoice/' + orderData.bill_id + '?print=true';
          window.open(invoiceUrl, '_blank');
          this.showToast('Takeaway order created & invoice opened for printing!', 'success');
          this.triggerTakeawayOrderFlow();
        } else {
          this.showToast('Order sent to kitchen!', 'success');
          this.triggerDineInOrderFlow();
        }
      } catch (error) {
        console.error('Error creating order:', error);
        if (error.message.includes('Please add at least one valid item')) {
          this.showToast(error.message, 'error');
        } else {
          this.showToast('Failed to create order. Try again.', 'error');
        }
      } finally {
        this.isCreatingOrder = false;
      }
    },

    async sendToKitchenAndPrintKOT() {
      if (this.isCreatingOrder) return;
      if (!this.canSendOrder) return;

      this.isCreatingOrder = true;
      try {
        var orderData = await this.createOrderAPI();
        if (orderData === null) {
          this.showToast('Error Occured! Please try again', 'error');
          return;
        }
        if (this.orderType === 'takeaway') {
          this.lastOrderType = 'takeaway';
          var kotUrl = this.base_url + '/sale/kot/' + orderData.kot_id + '?print=true';
          window.open(kotUrl, '_blank');
          this.showToast('Takeaway order created & invoice opened for printing!', 'success');
          this.triggerTakeawayOrderFlow();
        } else {
          this.lastOrderType = 'dine';
          var kotUrl2 = this.base_url + '/sale/kot/' + orderData.kot_id + '?print=true';
          window.open(kotUrl2, '_blank');
          this.showToast('Order sent to kitchen & KOT opened for printing!', 'success');
          this.closeOrderModal();
          this.triggerDineInOrderFlow();
        }
      } catch (error) {
        if (error.message.includes('Please add at least one valid item')) {
          this.showToast(error.message, 'error');
        } else {
          this.showToast('Failed to create order. Try again.', 'error');
        }
      } finally {
        this.isCreatingOrder = false;
      }
    },

    async triggerDineInOrderFlow() {
      this.invalidateRelatedCaches('order');
      this.fetchActiveDineInKots();
      this.fetchActiveTables();
    },

    async triggerTakeawayOrderFlow() {
      await this.invalidateRelatedCaches('takeaway');
      await this.fetchActiveTakeawayOrders();
      await this.invalidateCache('billing');
    }
  }
};
