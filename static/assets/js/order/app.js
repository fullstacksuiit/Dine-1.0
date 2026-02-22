window.DinePay = window.DinePay || {};

new Vue({
  el: '#dashboardApp',
  delimiters: ['[[', ']]'],

  mixins: [
    DinePay.UtilsMixin,
    DinePay.CacheMixin,
    DinePay.TablesMixin,
    DinePay.OrderPadMixin,
    DinePay.KotMixin,
    DinePay.TakeawayMixin,
    DinePay.BillingMixin,
    DinePay.HistoryMixin,
    DinePay.MenuMgmtMixin,
    DinePay.SettingsMixin
  ],

  data: function () {
    return {
      activeTab: 'activeTables',
      dashboardTabs: [
        { id: 'activeTables', label: 'Active Tables', icon: '\uD83C\uDF7D\uFE0F', count: 0 },
        { id: 'activeDineInOrders', label: 'Active Dine-In Orders', icon: '\uD83D\uDCCB', count: 0 },
        { id: 'activeTakeawayOrders', label: 'Active Takeaway Orders', icon: '\uD83E\uDD61', count: 0 },
        { id: 'menu', label: 'Menu', icon: '\uD83D\uDCDC', count: 0 },
        { id: 'billingHistory', label: 'Billing History', icon: '\uD83D\uDCCA', count: 0 },
        { id: 'settings', label: 'Settings', icon: '\u2699\uFE0F', count: undefined }
      ],
      base_url: window.location.origin,
      userInfoLoaded: false,
      currentUser: {
        id: null,
        username: '',
        email: '',
        firstName: '',
        lastName: '',
        role: '',
        contact: '',
        active: true,
        restaurant: { id: null, name: '' },
        isStaff: false,
        isSuperuser: false,
        dateJoined: null,
        lastLogin: null
      }
    };
  },

  computed: {
    totalTables: function () {
      return this.tables.length || 20;
    },

    restaurantHasGstin: function () {
      var gstin = (this.restaurantSettings && this.restaurantSettings.gstin) ||
                  (this.currentUser && this.currentUser.restaurant && this.currentUser.restaurant.gstin);
      return gstin && gstin.trim().length > 0;
    },

    canSendOrder: function () {
      var hasValidItems = this.currentOrder.some(function (item) {
        return item.name.trim() && item.id && item.quantity > 0;
      });
      if (this.orderType === 'takeaway') return hasValidItems;
      return hasValidItems && this.table.trim();
    },

    totalItems: function () {
      return this.currentOrder
        .filter(function (item) { return item.name.trim() && item.id; })
        .reduce(function (total, item) { return total + (item.quantity || 0); }, 0);
    },

    modalTitle: function () {
      if (this.isEditingTable && this.table) {
        return 'Table ' + this.table + ' - Add Items';
      }
      return this.orderType === 'takeaway' ? '\uD83E\uDD61 New Takeaway Order' : '\uD83C\uDF7D\uFE0F New Dine-in Order';
    },

    takeawayBill: function () {
      return this.billing;
    },

    userDisplayName: function () {
      if (!this.userInfoLoaded) return 'Loading...';
      var fullName = ((this.currentUser.firstName || '') + ' ' + (this.currentUser.lastName || '')).trim();
      return fullName || this.currentUser.username || 'Unknown User';
    },

    userRoleDisplay: function () {
      if (!this.userInfoLoaded) return '';
      var roleMap = { 'OWNER': 'Owner', 'MANAGER': 'Manager', 'WAITER': 'Waiter', 'STAFF': 'Staff' };
      return roleMap[this.currentUser.role] || this.currentUser.role || 'Staff';
    },

    restaurantName: function () {
      if (!this.userInfoLoaded) return 'Loading...';
      return this.currentUser.restaurant.name || 'Unknown Restaurant';
    }
  },

  watch: {
    activeTables: {
      handler: function (newTables) {
        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeTables'; });
        if (tab) tab.count = newTables.length;
        if (this.analytics) this.analytics.activeTablesCount = newTables.length;
      },
      immediate: true
    },

    dishes: {
      handler: function (newDishes) {
        var tab = this.dashboardTabs.find(function (t) { return t.id === 'menu'; });
        if (tab) tab.count = newDishes.length;
      },
      immediate: true
    },

    billingHistory: {
      handler: function (newBills) {
        var tab = this.dashboardTabs.find(function (t) { return t.id === 'billingHistory'; });
        if (tab) tab.count = newBills.length;
      },
      immediate: true
    },

    activeKots: {
      handler: function (newKots) {
        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeDineInOrders'; });
        if (tab) tab.count = newKots.length;
      },
      immediate: true
    },

    activeTakeawayOrders: {
      handler: function (newOrders) {
        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeTakeawayOrders'; });
        if (tab) tab.count = newOrders.length;
      },
      immediate: true
    },

    currentOrder: {
      handler: function () {
        if (this.orderType === 'takeaway') {
          this.$nextTick(function () { this.calculateBilling(); }.bind(this));
        }
      },
      deep: true
    },

    orderType: function (newType) {
      if (newType === 'takeaway') this.calculateBilling();
    },

    showOrderModal: function (val) {
      var self = this;
      this.$nextTick(function () {
        if (val && self.orderType === 'dine') {
          if (self.table) {
            self.$nextTick(function () {
              var itemInput = Array.isArray(self.$refs.firstItemNameInput)
                ? self.$refs.firstItemNameInput[0]
                : self.$refs.firstItemNameInput;
              if (itemInput && itemInput.focus) itemInput.focus();
            });
          } else {
            var input = self.$refs.dineTableInput;
            if (input && input.focus) input.focus();
          }
        }
        if (val && self.orderType === 'takeaway' && self.$refs.firstItemNameInput) {
          var itemInput2 = Array.isArray(self.$refs.firstItemNameInput)
            ? self.$refs.firstItemNameInput[0]
            : self.$refs.firstItemNameInput;
          if (itemInput2 && itemInput2.focus) itemInput2.focus();
        }
      });
    }
  },

  mounted: function () {
    var self = this;

    this.fetchCurrentUser();
    this.fetchMenuData();
    this.refreshAllOrderTabs();
    this.loadBillingColumnPrefs();

    // Auto-refresh KOTs and takeaway orders every 30s
    this.kotRefreshInterval = setInterval(function () {
      if (document.visibilityState === 'visible') {
        if (self.activeTab === 'activeDineInOrders') {
          self.fetchActiveDineInKots();
        } else if (self.activeTab === 'activeTakeawayOrders') {
          self.fetchActiveTakeawayOrders();
        }
      }
    }, 30000);

    // Handle ?edit_bill= query param from billing history page
    var urlParams = new URLSearchParams(window.location.search);
    var editBillId = urlParams.get('edit_bill');
    if (editBillId) {
      this.$nextTick(function () {
        self.editBill({ id: editBillId });
        // Clean up URL
        window.history.replaceState({}, '', window.location.pathname);
      });
    }

    // Menu column control event listeners
    this.$nextTick(function () {
      document.addEventListener('change', function (event) {
        if (event.target.classList.contains('menu-col-toggle')) {
          self.applyMenuColumnPrefs();
        }
      });
    });
  },

  beforeDestroy: function () {
    if (this.kotRefreshInterval) clearInterval(this.kotRefreshInterval);
  },

  methods: {
    setActiveTab: function (tabId) {
      this.activeTab = tabId;

      switch (tabId) {
        case 'activeTables':
        case 'all':
          this.fetchActiveTables();
          break;
        case 'activeDineInOrders':
          if (!this.isCacheValid('activeDineInKots')) {
            this.fetchActiveDineInKots();
          } else {
            var kotData = this.getCache('activeDineInKots');
            this.pendingKots = kotData.pending || [];
            this.acceptedKots = kotData.accepted || [];
            this.activeKots = kotData.all || [];
          }
          break;
        case 'activeTakeawayOrders':
          if (!this.isCacheValid('activeTakeawayOrders')) {
            this.fetchActiveTakeawayOrders();
          } else {
            this.activeTakeawayOrders = this.getCache('activeTakeawayOrders');
          }
          break;
        case 'menu':
          if (!this.isCacheValid('menuData')) {
            this.fetchMenuData();
          } else {
            var menuData = this.getCache('menuData');
            this.courses = menuData.courses || [];
            this.dishes = menuData.dishes || [];
            this.orderedCourseIds = menuData.ordering || [];
          }
          break;
        case 'billingHistory':
          this.loadBillingColumnPrefs();
          this.setDefaultDateRange();
          if (!this.isCacheValid('billingHistory')) {
            this.loadBillingHistory();
          } else {
            var cachedData = this.getCache('billingHistory');
            this.billingHistory = cachedData.bills || [];
            this.billingSummary = cachedData.summary || { count: 0, total_sale: 0, avg: 0 };
            this.filterBillingHistory();
          }
          break;
        case 'settings':
          this.activeSettingsTab = 'restaurant';
          this.loadRestaurantSettings();
          this.loadTeamMembers();
          this.fetchSettingsTables();
          break;
      }
    },

    refreshAllOrderTabs: function () {
      this.invalidateRelatedCaches('order');
      this.invalidateRelatedCaches('takeaway');
      this.invalidateRelatedCaches('billing');
      this.invalidateRelatedCaches('team');
      this.invalidateRelatedCaches('user');
      this.invalidateRelatedCaches('menu');
      this.fetchActiveTables();
      this.fetchActiveDineInKots();
      this.fetchActiveTakeawayOrders();
    },

    async fetchCurrentUser() {
      if (this.isCacheValid('currentUser')) {
        this.currentUser = this.getCache('currentUser');
        this.userInfoLoaded = true;
        return;
      }

      try {
        var response = await axios.get(this.base_url + '/core/api/me/', {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });

        if (response.data) {
          this.currentUser = {
            id: response.data.id,
            username: response.data.username,
            email: response.data.email || '',
            firstName: response.data.first_name || '',
            lastName: response.data.last_name || '',
            role: response.data.role || '',
            contact: response.data.contact || '',
            active: response.data.active !== false,
            restaurant: {
              id: (response.data.restaurant && response.data.restaurant.id) || null,
              name: (response.data.restaurant && (response.data.restaurant.name || response.data.restaurant.display_name)) || '',
              contact: (response.data.restaurant && response.data.restaurant.contact) || '',
              street_address: (response.data.restaurant && response.data.restaurant.street_address) || '',
              locality: (response.data.restaurant && response.data.restaurant.locality) || '',
              city: (response.data.restaurant && response.data.restaurant.city) || '',
              district: (response.data.restaurant && response.data.restaurant.district) || '',
              state: (response.data.restaurant && response.data.restaurant.state) || '',
              country: (response.data.restaurant && response.data.restaurant.country) || 'India',
              pincode: (response.data.restaurant && response.data.restaurant.pincode) || '',
              gstin: (response.data.restaurant && response.data.restaurant.gstin) || '',
              upi_id: (response.data.restaurant && response.data.restaurant.upi_id) || '',
              full_address: (response.data.restaurant && response.data.restaurant.full_address) || '',
              tables: (response.data.restaurant && response.data.restaurant.tables) || []
            },
            isStaff: response.data.is_staff || false,
            isSuperuser: response.data.is_superuser || false,
            dateJoined: response.data.date_joined || null,
            lastLogin: response.data.last_login || null
          };
          this.userInfoLoaded = true;

          if (this.currentUser.restaurant.tables && this.currentUser.restaurant.tables.length > 0) {
            this.tables = this.currentUser.restaurant.tables;
          }

          this.setCache('currentUser', this.currentUser);
        }
      } catch (error) {
        console.error('Error fetching current user info:', error);
        this.userInfoLoaded = false;
        this.currentUser = {
          id: null, username: 'Unknown User', email: '', firstName: '', lastName: '',
          role: 'UNKNOWN', contact: '', active: false,
          restaurant: { id: null, name: 'Unknown Restaurant' },
          isStaff: false, isSuperuser: false, dateJoined: null, lastLogin: null
        };
      }
    }
  }
});
