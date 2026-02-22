window.DinePay = window.DinePay || {};

DinePay.KotMixin = {
  data: function () {
    return {
      pendingKots: [],
      acceptedKots: [],
      activeKots: [],
      kotRefreshInterval: null
    };
  },

  methods: {
    async fetchActiveDineInKots() {
      try {
        if (this.isCacheValid('activeDineInKots')) {
          var kotData = this.getCache('activeDineInKots');
          this.pendingKots = kotData.pending || [];
          this.acceptedKots = kotData.accepted || [];
          this.activeKots = kotData.all || [];

          var activeDineInOrdersTab = this.dashboardTabs.find(function (tab) { return tab.id === 'activeDineInOrders'; });
          if (activeDineInOrdersTab) activeDineInOrdersTab.count = this.pendingKots.length + this.acceptedKots.length;
          return;
        }

        var response = await axios.get(this.base_url + '/sale/api/kots/?filter=dine-in', {
          headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' }
        });

        if (response.data.pending_kots !== undefined && response.data.accepted_kots !== undefined) {
          this.pendingKots = response.data.pending_kots || [];
          this.acceptedKots = response.data.accepted_kots || [];
          this.activeKots = [].concat(this.pendingKots, this.acceptedKots);
        } else {
          var kots = response.data || [];
          this.pendingKots = kots.filter(function (kot) {
            return !kot.accepted && kot.status === 'PENDING';
          }).sort(function (a, b) { return new Date(a.created_at) - new Date(b.created_at); });
          this.acceptedKots = kots.filter(function (kot) {
            return kot.status !== 'CANCELLED' && kot.status !== 'PENDING';
          }).sort(function (a, b) { return new Date(a.created_at) - new Date(b.created_at); });
          this.activeKots = kots;
        }

        this.setCache('activeDineInKots', {
          pending: this.pendingKots,
          accepted: this.acceptedKots,
          all: this.activeKots
        });

        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeDineInOrders'; });
        if (tab) tab.count = this.pendingKots.length + this.acceptedKots.length;

      } catch (error) {
        console.error('Error fetching active KOTs:', error);
        this.activeKots = [];
        this.pendingKots = [];
        this.acceptedKots = [];
      }
    },

    async acceptKot(kotId) {
      try {
        var response = await axios.patch(this.base_url + '/sale/api/kots/' + kotId, {
          status: 'IN_PROGRESS'
        }, {
          headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' }
        });

        if (response.status === 200) {
          var kotIndex = this.pendingKots.findIndex(function (k) { return k.id === kotId; });
          if (kotIndex !== -1) {
            var kot = this.pendingKots[kotIndex];
            kot.status = 'IN_PROGRESS';
            kot.accepted = true;
            this.pendingKots.splice(kotIndex, 1);
            this.acceptedKots.unshift(kot);

            var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeDineInOrders'; });
            if (tab) tab.count = this.pendingKots.length + this.acceptedKots.length;
          }
        } else {
          this.showToast('Failed to accept KOT. Please try again.', 'error');
        }
      } catch (error) {
        this.showToast('Failed to accept KOT. Please try again.', 'error');
      }
    },

    async acceptAllPendingKots() {
      if (this.pendingKots.length === 0) return;

      if (!confirm('Are you sure you want to accept all ' + this.pendingKots.length + ' pending KOTs?')) return;

      var self = this;
      var originalPendingKots = this.pendingKots.slice();
      var successCount = 0;
      var failureCount = 0;

      var acceptAllButton = document.querySelector('.btn-accept-all');
      if (acceptAllButton) {
        acceptAllButton.textContent = 'Processing...';
        acceptAllButton.disabled = true;
      }

      try {
        var acceptPromises = originalPendingKots.map(async function (kot) {
          try {
            var response = await axios.patch(self.base_url + '/sale/api/kots/' + kot.id, {
              status: 'IN_PROGRESS'
            }, {
              headers: { 'X-CSRFToken': self.getCsrfToken(), 'Content-Type': 'application/json' }
            });

            if (response.status === 200) {
              successCount++;
              return { success: true, kot: kot };
            } else {
              failureCount++;
              return { success: false, kot: kot };
            }
          } catch (error) {
            failureCount++;
            return { success: false, kot: kot, error: error };
          }
        });

        var results = await Promise.all(acceptPromises);

        results.forEach(function (result) {
          if (result.success) {
            var kotIndex = self.pendingKots.findIndex(function (k) { return k.id === result.kot.id; });
            if (kotIndex !== -1) {
              var kot = self.pendingKots[kotIndex];
              kot.status = 'IN_PROGRESS';
              kot.accepted = true;
              self.pendingKots.splice(kotIndex, 1);
              self.acceptedKots.unshift(kot);
            }
          }
        });

        var tab = this.dashboardTabs.find(function (t) { return t.id === 'activeDineInOrders'; });
        if (tab) tab.count = this.pendingKots.length + this.acceptedKots.length;

        if (failureCount === 0) {
          this.showToast('Successfully accepted all ' + successCount + ' KOTs!', 'success');
        } else if (successCount === 0) {
          this.showToast('Failed to accept any KOTs. Please try again.', 'error');
        } else {
          this.showToast('Accepted ' + successCount + ' KOTs successfully. ' + failureCount + ' failed - please retry those individually.', 'warning');
        }
      } catch (error) {
        this.showToast('An error occurred while accepting KOTs. Please try again.', 'error');
      } finally {
        if (acceptAllButton) {
          acceptAllButton.disabled = false;
          acceptAllButton.textContent = '\u2705 Accept All (' + this.pendingKots.length + ')';
        }
      }
    },

    async updateKotStatus(kotId, newStatus) {
      try {
        await axios.patch(this.base_url + '/sale/api/kots/' + kotId, {
          status: newStatus
        }, {
          headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' }
        });

        var kot = this.activeKots.find(function (k) { return k.id === kotId; });
        if (kot) kot.status = newStatus;
      } catch (error) {
        console.error('Error updating KOT status:', error);
        alert('Failed to update status. Please try again.');
      }
    },

    viewKot(kotId) {
      window.open(this.base_url + '/sale/kot/' + kotId, '_blank');
    }
  }
};
