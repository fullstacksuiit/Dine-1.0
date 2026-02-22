window.DinePay = window.DinePay || {};

DinePay.TablesMixin = {
  data: function () {
    return {
      tables: [],
      activeTables: [],
      showMergeModal: false,
      mergeSourceTable: null,
      showExistingOrdersModal: false,
      existingOrders: [],
      tableEdit: {
        editingTableId: null,
        originalTableNumber: '',
        newTableNumber: '',
        isLoading: false
      }
    };
  },

  methods: {
    async fetchActiveTables() {
      try {
        if (this.isCacheValid('activeTables')) {
          this.activeTables = this.getCache('activeTables');
          var activeTablesTab = this.dashboardTabs.find(function (tab) { return tab.id === 'activeTables'; });
          if (activeTablesTab) activeTablesTab.count = this.activeTables.length;
          return;
        }
        var response = await axios.get(this.base_url + '/sale/api/orders/');
        this.activeTables = response.data.active_tables || [];
        this.setCache('activeTables', this.activeTables);

        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeTables'; });
        if (tab) tab.count = this.activeTables.length;
      } catch (error) {
        console.error('Error fetching active tables:', error);
        this.activeTables = [];
      }
    },

    isTableOccupied(n) {
      return this.activeTables.some(function (t) { return String(t.table_number) === String(n); });
    },

    onOverviewTableClick(n) {
      var activeTable = this.activeTables.find(function (t) { return String(t.table_number) === String(n); });
      if (activeTable) {
        this.openTableModal(activeTable);
      } else {
        this.table = String(n);
        this.openNewOrderModal();
      }
    },

    openTableModal(table) {
      this.currentTableId = table.id;
      this.currentTable = table.table_number;
      this.fetchExistingOrders(table.id);
      this.showExistingOrdersModal = true;
    },

    closeExistingOrdersModal() {
      this.showExistingOrdersModal = false;
      this.existingOrders = [];
      this.currentTableId = null;
      this.currentTable = '';
    },

    closeExistingOrdersModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeExistingOrdersModal();
    },

    async fetchExistingOrders(billId) {
      try {
        var response = await axios.get(this.base_url + '/sale/api/bills/' + encodeURIComponent(billId) + '?group=false');
        this.existingOrders = response.data.orders || [];
      } catch (error) {
        console.error('Error fetching existing orders:', error);
        alert('Error fetching table data. Please try again.');
      }
    },

    increaseOrderQuantity(index) {
      this.existingOrders[index].quantity += 1;
      this.updateOrderData(index);
    },

    decreaseOrderQuantity(index) {
      var order = this.existingOrders[index];
      if (order.quantity > 1) {
        order.quantity -= 1;
        this.updateOrderData(index);
      }
    },

    updateOrderSize(index) {
      this.updateOrderData(index);
    },

    updateOrderData(index) {
      var self = this;
      var order = this.existingOrders[index];

      if (this.quantityUpdateTimeout) clearTimeout(this.quantityUpdateTimeout);

      this.quantityUpdateTimeout = setTimeout(function () {
        axios.patch(self.base_url + '/sale/api/orders/' + encodeURIComponent(order.id), {
          quantity: order.quantity,
          size: order.size
        }, {
          headers: { 'X-CSRFToken': self.getCsrfToken() }
        })
        .then(function () { self.showToast('Order Updated'); })
        .catch(function (error) {
          console.error('Error updating order:', error);
          alert('Failed to update item. Please try again.');
          self.invalidateRelatedCaches('order');
          self.fetchExistingOrders(self.currentTableId);
        });
      }, 500);
    },

    removeOrder(index) {
      if (!confirm('Are you sure you want to remove this dish from the order?')) return;
      var self = this;
      var order = this.existingOrders[index];

      axios.delete(this.base_url + '/sale/api/orders/' + encodeURIComponent(order.id), {
        headers: { 'X-CSRFToken': this.getCsrfToken() }
      })
      .then(function () {
        self.invalidateCache('activeTables');
        self.fetchExistingOrders(self.currentTableId);
      })
      .catch(function (error) {
        console.error('Error removing order:', error);
        alert('Failed to remove item. Please try again.');
      });
    },

    addMoreItems() {
      this.showExistingOrdersModal = false;
      this.isEditingTable = true;
      this.table = this.currentTable;
      this.orderType = 'dine';
      this.resetOrderItems();
      this.showOrderModal = true;
    },

    addItemsToTable(table) {
      this.currentTableId = table.id;
      this.currentTable = table.table_number;
      this.isEditingTable = true;
      this.table = table.table_number;
      this.orderType = 'dine';
      this.resetOrderItems();
      this.showOrderModal = true;
    },

    generateBillForTable(table) {
      this.currentTableId = table.id;
      this.currentTable = table.table_number;
      this.initializeBilling();
      this.showBillingModal = true;
    },

    async _deleteTable(tableId, confirmMsg, afterDelete) {
      if (!confirm(confirmMsg)) return;
      try {
        await axios.delete(this.base_url + '/sale/api/bills/' + encodeURIComponent(tableId), {
          headers: { 'X-CSRFToken': this.getCsrfToken() }
        });
        if (typeof afterDelete === 'function') afterDelete();
        this.invalidateRelatedCaches('order');
        this.triggerDineInOrderFlow();
      } catch (error) {
        console.error('Error discarding table:', error);
        alert('Failed to delete table. ' + (error.response && error.response.data ? error.response.data.message || '' : ''));
      }
    },

    discardTable() {
      var self = this;
      this._deleteTable(
        this.currentTableId,
        'Are you sure you want to delete this table and all its orders?',
        function () { self.closeExistingOrdersModal(); }
      );
    },

    discardTableDirect(table) {
      this._deleteTable(
        table.id,
        'Are you sure you want to delete Table ' + table.table_number + ' and all its orders?'
      );
    },

    // Merge table methods
    startMergeTable(table) {
      this.mergeSourceTable = table;
      this.showMergeModal = true;
    },

    closeMergeModal() {
      this.showMergeModal = false;
      this.mergeSourceTable = null;
    },

    async confirmMergeTable(targetTable) {
      var sourceNum = this.mergeSourceTable.table_number;
      var targetNum = targetTable.table_number;
      if (!confirm('Merge Table #' + sourceNum + ' into Table #' + targetNum + '?\n\nAll orders from Table #' + sourceNum + ' will move to Table #' + targetNum + '.')) {
        return;
      }
      try {
        var response = await axios.post(
          this.base_url + '/sale/api/bills/' + targetTable.id + '/merge/',
          { source_bill_id: this.mergeSourceTable.id },
          {
            headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' },
            withCredentials: true
          }
        );
        if (response.status === 200 && response.data.merged) {
          this.showToast('Table #' + sourceNum + ' merged into Table #' + targetNum + ' (' + response.data.orders_transferred + ' orders moved)', 'success');
          this.closeMergeModal();
          this.invalidateAllCaches();
        } else {
          this.showToast('Failed to merge tables. Please try again.', 'error');
        }
      } catch (error) {
        var msg = (error.response && error.response.data && error.response.data.detail) || 'Failed to merge tables.';
        this.showToast(msg, 'error');
      }
    },

    // Inline table edit methods
    startTableEdit(table) {
      this.tableEdit.editingTableId = table.id;
      this.tableEdit.originalTableNumber = table.table_number;
      this.tableEdit.newTableNumber = table.table_number;

      this.$nextTick(function () {
        var input = document.querySelector('.table-edit-input');
        if (input) { input.focus(); input.select(); }
      });
    },

    cancelTableEdit() {
      this.tableEdit.editingTableId = null;
      this.tableEdit.originalTableNumber = '';
      this.tableEdit.newTableNumber = '';
      this.tableEdit.isLoading = false;
    },

    async saveTableEdit() {
      if (!this.tableEdit.newTableNumber.trim()) {
        this.showToast('Table number cannot be empty', 'error');
        return;
      }

      if (this.tableEdit.newTableNumber === this.tableEdit.originalTableNumber) {
        this.cancelTableEdit();
        return;
      }

      this.tableEdit.isLoading = true;

      try {
        var response = await this.apiPatchTableNumber(this.tableEdit.editingTableId, this.tableEdit.newTableNumber);
        var updatedTable = response.data;

        var tableIndex = this.activeTables.findIndex(function (t) { return t.id === updatedTable.id; });
        if (tableIndex !== -1) this.activeTables[tableIndex] = updatedTable;

        this.showToast('Table number updated to ' + this.tableEdit.newTableNumber, 'success');
        this.cancelTableEdit();
      } catch (error) {
        console.error('Error updating table number:', error);
        this.showToast(error.message || 'Failed to update table number. Please try again.', 'error');
      } finally {
        this.tableEdit.isLoading = false;
      }
    },

    apiPatchTableNumber(tableId, tableNumber) {
      return axios.patch(this.base_url + '/sale/api/bills/' + tableId, {
        table_number: tableNumber.trim()
      }, {
        headers: { 'X-CSRFToken': this.getCsrfToken() }
      });
    }
  }
};
