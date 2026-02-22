window.DinePay = window.DinePay || {};

DinePay.HistoryMixin = {
  data: function () {
    return {
      loadingBillingHistory: false,
      billingHistory: [],
      filteredBillingHistory: [],
      paginatedBillingHistory: [],
      billingSearchQuery: '',
      billingFilter: {
        quickRange: 'today',
        fromDate: '',
        toDate: '',
        orderType: 'ALL',
        paymentType: 'ALL',
        paymentStatus: 'ALL'
      },
      billingColumns: {
        invoice: true,
        datetime: true,
        subtotal: true,
        discount: true,
        total: true,
        status: true,
        actions: true
      },
      billingSummary: {
        count: 0,
        total: 0,
        average: 0
      },
      billingSort: {
        column: '',
        direction: 'asc'
      },
      billingPagination: {
        currentPage: 1,
        pageSize: 20,
        totalPages: 0,
        totalRecords: 0
      }
    };
  },

  methods: {
    setDefaultDateRange() {
      var today = this.getISTDate();
      var formatDate = function (date) {
        var year = date.getFullYear();
        var month = String(date.getMonth() + 1).padStart(2, '0');
        var day = String(date.getDate()).padStart(2, '0');
        return year + '-' + month + '-' + day;
      };

      switch (this.billingFilter.quickRange) {
        case 'today':
          this.billingFilter.fromDate = formatDate(today);
          this.billingFilter.toDate = formatDate(today);
          break;
        case 'yesterday':
          var yesterday = new Date(today);
          yesterday.setDate(yesterday.getDate() - 1);
          this.billingFilter.fromDate = formatDate(yesterday);
          this.billingFilter.toDate = formatDate(yesterday);
          break;
        case 'last7':
          var lastWeek = new Date(today);
          lastWeek.setDate(lastWeek.getDate() - 7);
          this.billingFilter.fromDate = formatDate(lastWeek);
          this.billingFilter.toDate = formatDate(today);
          break;
        case 'last30':
          var lastMonth = new Date(today);
          lastMonth.setDate(lastMonth.getDate() - 30);
          this.billingFilter.fromDate = formatDate(lastMonth);
          this.billingFilter.toDate = formatDate(today);
          break;
        case 'this_month':
          var thisMonthStart = new Date(today.getFullYear(), today.getMonth(), 1);
          this.billingFilter.fromDate = formatDate(thisMonthStart);
          this.billingFilter.toDate = formatDate(today);
          break;
        case 'last_month':
          var lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
          var lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
          this.billingFilter.fromDate = formatDate(lastMonthStart);
          this.billingFilter.toDate = formatDate(lastMonthEnd);
          break;
        case 'last_year':
          var lastYear = new Date(today);
          lastYear.setFullYear(lastYear.getFullYear() - 1);
          this.billingFilter.fromDate = formatDate(lastYear);
          this.billingFilter.toDate = formatDate(today);
          break;
        case 'current_fiscal_year':
          var currentYear = today.getFullYear();
          var fiscalYearStart;
          if (today.getMonth() >= 3) {
            fiscalYearStart = new Date(currentYear, 3, 1);
          } else {
            fiscalYearStart = new Date(currentYear - 1, 3, 1);
          }
          this.billingFilter.fromDate = formatDate(fiscalYearStart);
          this.billingFilter.toDate = formatDate(today);
          break;
        case 'previous_fiscal_year':
          var prevYear = today.getFullYear();
          var prevFiscalStart, prevFiscalEnd;
          if (today.getMonth() >= 3) {
            prevFiscalStart = new Date(prevYear - 1, 3, 1);
            prevFiscalEnd = new Date(prevYear, 2, 31);
          } else {
            prevFiscalStart = new Date(prevYear - 2, 3, 1);
            prevFiscalEnd = new Date(prevYear - 1, 2, 31);
          }
          this.billingFilter.fromDate = formatDate(prevFiscalStart);
          this.billingFilter.toDate = formatDate(prevFiscalEnd);
          break;
      }
    },

    onQuickRangeChange() {
      this.setDefaultDateRange();
      this.loadBillingHistory();
    },

    async loadBillingHistory() {
      this.loadingBillingHistory = true;
      try {
        var params = new URLSearchParams({
          from: this.billingFilter.fromDate,
          to: this.billingFilter.toDate,
          order_type: this.billingFilter.orderType,
          payment_type: this.billingFilter.paymentType,
          payment_status: this.billingFilter.paymentStatus,
          page: this.billingPagination.currentPage,
          page_size: this.billingPagination.pageSize
        });

        var searchTerm = this.billingSearchQuery.trim();
        if (searchTerm) {
          params.set('search', searchTerm);
        }

        var response = await axios.get(this.base_url + '/sale/api/billing-history/?' + params);

        if (response.data) {
          this.billingHistory = response.data.bills || [];
          this.billingSummary = response.data.summary || { count: 0, total_sale: 0, avg: 0 };

          // Use server-side pagination metadata
          if (response.data.pagination) {
            this.billingPagination.totalRecords = response.data.pagination.count;
            this.billingPagination.totalPages = response.data.pagination.num_pages;
            this.billingPagination.currentPage = response.data.pagination.current_page;
          } else {
            this.billingPagination.totalRecords = this.billingHistory.length;
            this.billingPagination.totalPages = 1;
            this.billingPagination.currentPage = 1;
          }

          // Bills are already paginated by server
          this.filteredBillingHistory = this.billingHistory;
          this.paginatedBillingHistory = this.billingHistory;

          this.setCache('billingHistory', {
            bills: this.billingHistory,
            summary: this.billingSummary
          });
        } else {
          this.billingHistory = [];
          this.billingSummary = { count: 0, total_sale: 0, avg: 0 };
          this.filteredBillingHistory = [];
          this.paginatedBillingHistory = [];
        }
      } catch (error) {
        console.error('Failed to load billing history:', error);
        this.showToast('Failed to load billing history. Please try again.', 'error');
        this.billingHistory = [];
        this.billingSummary = { count: 0, total_sale: 0, avg: 0 };
        this.filteredBillingHistory = [];
        this.paginatedBillingHistory = [];
      } finally {
        this.loadingBillingHistory = false;
      }
    },

    filterBillingHistory() {
      // Search is now server-side — reset to page 1 and re-fetch
      this.billingPagination.currentPage = 1;
      this.loadBillingHistory();
    },

    onBillingSearchInput() {
      // Debounce search to avoid API call on every keystroke
      clearTimeout(this._billingSearchDebounce);
      this._billingSearchDebounce = setTimeout(function () {
        this.filterBillingHistory();
      }.bind(this), 300);
    },

    updateBillingPagination() {
      // Pagination is now server-driven; this is kept for compatibility
      this.paginatedBillingHistory = this.billingHistory;
    },

    changeBillingPage(page) {
      if (page >= 1 && page <= this.billingPagination.totalPages) {
        this.billingPagination.currentPage = page;
        this.loadBillingHistory();
      }
    },

    sortBillingHistory(column) {
      if (this.billingSort.column === column) {
        this.billingSort.direction = this.billingSort.direction === 'asc' ? 'desc' : 'asc';
      } else {
        this.billingSort.column = column;
        this.billingSort.direction = 'asc';
      }

      this.filteredBillingHistory.sort(function (a, b) {
        var aVal = a[column];
        var bVal = b[column];

        if (column === 'total') {
          aVal = parseFloat(a.amount || a.total || 0);
          bVal = parseFloat(b.amount || b.total || 0);
        } else if (column === 'subtotal') {
          aVal = parseFloat(a.sub_total || a.subtotal || 0);
          bVal = parseFloat(b.sub_total || b.subtotal || 0);
        } else if (column === 'invoice') {
          aVal = a.full_invoice_number || a.invoice_number || '';
          bVal = b.full_invoice_number || b.invoice_number || '';
        }

        if (this.billingSort.direction === 'asc') {
          return aVal > bVal ? 1 : -1;
        } else {
          return aVal < bVal ? 1 : -1;
        }
      }.bind(this));

      this.updateBillingPagination();
    },

    getSortClass(column) {
      if (this.billingSort.column === column) {
        return this.billingSort.direction === 'asc' ? 'asc' : 'desc';
      }
      return '';
    },

    async settleBill(billId, paymentType) {
      if (!paymentType) return;
      try {
        await axios.post(this.base_url + '/sale/api/bills/' + billId + '/settle/', {
          payment_type: paymentType
        }, {
          headers: { 'X-CSRFToken': this.getCsrfToken() }
        });
        this.showToast('Bill settled as ' + paymentType, 'success');
        this.invalidateRelatedCaches('billing');
        this.loadBillingHistory();
      } catch (error) {
        console.error('Failed to settle bill:', error);
        this.showToast('Failed to settle bill', 'error');
        this.loadBillingHistory();
      }
    },

    viewBillInvoice(bill) {
      window.open(this.base_url + '/sale/invoice/' + bill.id, '_blank');
    },

    editBill(bill) {
      this.billingMode = 'edit';
      this.editingBillId = bill.id;
      this.currentTableId = bill.id;
      this.openBillingModal();
    },

    async deleteBill(bill) {
      var invoiceNumber = bill.full_invoice_number || bill.invoice_number;
      if (!confirm('Are you sure you want to delete bill ' + invoiceNumber + '? This cannot be undone.')) return;

      try {
        await axios.delete(this.base_url + '/sale/api/bills/' + bill.id);
        this.showToast('Bill deleted successfully', 'success');
        this.invalidateRelatedCaches('billing');
        this.loadBillingHistory();
      } catch (error) {
        console.error('Failed to delete bill:', error);
        this.showToast('Failed to delete bill. Please check your permissions.', 'error');
      }
    },

    saveBillingColumnPrefs() {
      localStorage.setItem('billing_history_columns', JSON.stringify(this.billingColumns));
    },

    loadBillingColumnPrefs() {
      var saved = localStorage.getItem('billing_history_columns');
      if (saved) {
        try {
          this.billingColumns = Object.assign({}, this.billingColumns, JSON.parse(saved));
        } catch (error) {
          console.error('Failed to load column preferences:', error);
        }
      }
    },

    async downloadReport(reportType) {
      reportType = reportType || 'BILL';
      var self = this;
      try {
        var formData = new FormData();
        formData.append('from', this.billingFilter.fromDate);
        formData.append('to', this.billingFilter.toDate);
        formData.append('order_type', this.billingFilter.orderType);
        formData.append('payment_type', this.billingFilter.paymentType);
        formData.append('report_type', reportType);
        formData.append('csrfmiddlewaretoken', this.getCsrfToken());

        var buttonClass = reportType === 'DISH' ? '.download-dish-report-btn' : '.download-report-btn';
        var downloadButton = document.querySelector(buttonClass);
        var originalHTML = downloadButton ? downloadButton.innerHTML : '';

        if (downloadButton) {
          downloadButton.disabled = true;
          downloadButton.innerHTML = '<span>\u23F3</span><span>Generating...</span>';
        }

        var response = await this.apiPostDownloadReport(formData);

        if (!response.ok) throw new Error('HTTP error! status: ' + response.status);

        var contentDisposition = response.headers.get('Content-Disposition');
        var filename = reportType.toLowerCase() + '_report.xlsx';

        if (contentDisposition) {
          var filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1].replace(/['"]/g, '');
          }
        } else {
          var today = new Date().toISOString().split('T')[0];
          var filterSuffix = this.billingFilter.quickRange !== 'custom'
            ? '_' + this.billingFilter.quickRange
            : '_' + this.billingFilter.fromDate + '_to_' + this.billingFilter.toDate;
          filename = reportType.toLowerCase() + '_report_' + today + filterSuffix + '.xlsx';
        }

        var blob = await response.blob();
        var downloadUrl = window.URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);

        this.showToast((reportType === 'BILL' ? 'Bills' : 'Dishes') + ' report downloaded successfully!', 'success');
      } catch (error) {
        console.error('Error downloading report:', error);
        this.showToast('Failed to download ' + (reportType === 'BILL' ? 'bills' : 'dishes') + ' report. Please try again.', 'error');
      } finally {
        var btnClass = reportType === 'DISH' ? '.download-dish-report-btn' : '.download-report-btn';
        var btn = document.querySelector(btnClass);
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = reportType === 'DISH'
            ? '<span>\uD83C\uDF7D\uFE0F</span><span>Dishes Report</span>'
            : '<span>\uD83D\uDCCA</span><span>Bills Report</span>';
        }
      }
    },

    apiPostDownloadReport(formData) {
      return fetch('/sale/report/', {
        method: 'POST',
        headers: { 'X-CSRFToken': this.getCsrfToken() },
        body: formData
      });
    }
  }
};
