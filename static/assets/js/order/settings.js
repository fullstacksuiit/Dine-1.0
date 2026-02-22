window.DinePay = window.DinePay || {};

DinePay.SettingsMixin = {
  data: function () {
    return {
      activeSettingsTab: 'restaurant',
      restaurantSettings: {
        id: null,
        name: '',
        contact: '',
        street_address: '',
        locality: '',
        city: '',
        district: '',
        state: '',
        country: 'India',
        pincode: '',
        gstin: '',
        upi_id: '',
        num_tables: 20,
        address: '',
        phone: '',
        gst: '',
        taxRate: 5.0,
        serviceCharge: 0.0
      },
      settingsTables: [],
      teamMembers: [],
      showTeamMemberModal: false,
      editingTeamMember: false,
      teamMemberForm: {
        id: null,
        username: '',
        role: 'WAITER',
        contact: '',
        password: '',
        active: true
      },
      newTableName: '',
      quickAddCount: '',
      editingTableId: null,
      editingTableName: ''
    };
  },

  methods: {
    async loadRestaurantSettings() {
      this.activeSettingsTab = 'restaurant';
      try {
        await this.fetchCurrentUser();

        if (this.currentUser && this.currentUser.restaurant) {
          var restaurant = this.currentUser.restaurant;
          this.restaurantSettings = {
            id: restaurant.id || null,
            name: restaurant.name || '',
            contact: restaurant.contact || '',
            street_address: restaurant.street_address || '',
            locality: restaurant.locality || '',
            city: restaurant.city || '',
            district: restaurant.district || '',
            state: restaurant.state || '',
            country: restaurant.country || 'India',
            pincode: restaurant.pincode || '',
            gstin: restaurant.gstin || '',
            upi_id: restaurant.upi_id || '',
            num_tables: restaurant.num_tables || 20
          };
        } else {
          this.restaurantSettings = {
            id: null, name: '', contact: '', street_address: '', locality: '',
            city: '', district: '', state: '', country: 'India', pincode: '',
            gstin: '', upi_id: '', num_tables: 20
          };
        }
      } catch (error) {
        console.error('Failed to load restaurant settings:', error);
        this.showToast('Failed to load restaurant settings', 'error');
      }
    },

    async saveRestaurantSettings() {
      try {
        if (!this.restaurantSettings.name || !this.restaurantSettings.name.trim()) {
          this.showToast('Restaurant name is required', 'error');
          return;
        }

        var payload = {
          name: this.restaurantSettings.name.trim(),
          contact: this.restaurantSettings.contact.trim(),
          street_address: this.restaurantSettings.street_address.trim(),
          locality: this.restaurantSettings.locality.trim(),
          city: this.restaurantSettings.city.trim(),
          district: this.restaurantSettings.district.trim(),
          state: this.restaurantSettings.state.trim(),
          country: this.restaurantSettings.country.trim() || 'India',
          pincode: this.restaurantSettings.pincode.trim(),
          gstin: this.restaurantSettings.gstin.trim(),
          upi_id: this.restaurantSettings.upi_id.trim(),
          num_tables: parseInt(this.restaurantSettings.num_tables) || 20
        };

        var response = await axios.put(this.base_url + '/core/api/restaurant-settings/', payload, {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });

        this.showToast('Restaurant settings saved successfully', 'success');
        this.invalidateRelatedCaches('user');

        if (this.currentUser && this.currentUser.restaurant) {
          Object.assign(this.currentUser.restaurant, response.data);
          this.setCache('currentUser', this.currentUser);
        }
        this.showToast('Settings updated');
      } catch (error) {
        console.error('Failed to save restaurant settings:', error);

        var message = 'Failed to save restaurant settings';
        if (error.response && error.response.data && error.response.data.message) {
          message = error.response.data.message;
        } else if (error.response && error.response.data && error.response.data.error) {
          message = error.response.data.error;
        } else if (error.response && error.response.status === 403) {
          message = 'You do not have permission to update restaurant settings';
        } else if (error.response && error.response.status === 404) {
          message = 'Restaurant not found';
        } else if (error.message) {
          message = error.message;
        }

        this.showToast(message, 'error');
      }
    },

    // Table management methods
    async fetchSettingsTables() {
      try {
        var response = await axios.get(this.base_url + '/core/api/tables/', {
          headers: { 'X-CSRFToken': this.getCSRFToken() }
        });
        this.settingsTables = response.data;
      } catch (error) {
        console.error('Failed to fetch tables:', error);
      }
    },

    async addNewTable() {
      var name = this.newTableName.trim();
      if (!name) {
        this.showToast('Please enter a table name', 'error');
        return;
      }
      try {
        await axios.post(this.base_url + '/core/api/tables/', { name: name }, {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });
        this.newTableName = '';
        await this.fetchSettingsTables();
        this.tables = this.settingsTables;
        this.invalidateRelatedCaches('user');
        this.showToast('Table added');
      } catch (error) {
        this.showToast((error.response && error.response.data && error.response.data.error) || 'Failed to add table', 'error');
      }
    },

    async deleteSettingsTable(tableId) {
      if (!confirm('Remove this table?')) return;
      try {
        await axios.delete(this.base_url + '/core/api/tables/' + tableId, {
          headers: { 'X-CSRFToken': this.getCSRFToken() }
        });
        await this.fetchSettingsTables();
        this.tables = this.settingsTables;
        this.invalidateRelatedCaches('user');
        this.showToast('Table removed');
      } catch (error) {
        this.showToast((error.response && error.response.data && error.response.data.error) || 'Failed to remove table', 'error');
      }
    },

    startEditSettingsTable(table) {
      this.editingTableId = table.id;
      this.editingTableName = table.name;
    },

    cancelEditSettingsTable() {
      this.editingTableId = null;
      this.editingTableName = '';
    },

    async saveEditSettingsTable() {
      var name = this.editingTableName.trim();
      if (!name) {
        this.showToast('Table name cannot be empty', 'error');
        return;
      }
      try {
        await axios.put(this.base_url + '/core/api/tables/' + this.editingTableId, { name: name }, {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });
        this.editingTableId = null;
        this.editingTableName = '';
        await this.fetchSettingsTables();
        this.tables = this.settingsTables;
        this.invalidateRelatedCaches('user');
        this.showToast('Table renamed');
      } catch (error) {
        this.showToast((error.response && error.response.data && error.response.data.error) || 'Failed to rename table', 'error');
      }
    },

    async quickAddTables() {
      var count = parseInt(this.quickAddCount);
      if (!count || count < 1 || count > 200) {
        this.showToast('Enter a number between 1 and 200', 'error');
        return;
      }
      var added = 0;
      for (var i = 1; i <= count; i++) {
        try {
          await axios.post(this.base_url + '/core/api/tables/', { name: String(i), display_order: i }, {
            headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
          });
          added++;
        } catch (e) {
          // Skip duplicates
        }
      }
      this.quickAddCount = '';
      await this.fetchSettingsTables();
      this.tables = this.settingsTables;
      this.invalidateRelatedCaches('user');
      if (added > 0) {
        this.showToast(added + ' table(s) added');
      } else {
        this.showToast('All tables already exist', 'error');
      }
    },

    // Team member methods
    async loadTeamMembers() {
      try {
        var response = await axios.get(this.base_url + '/core/api/team/', {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });
        if (response.data) {
          this.teamMembers = response.data.results || response.data || [];
        }
      } catch (error) {
        console.error('Failed to load team members:', error);
        this.showToast('Failed to load team members', 'error');
        this.teamMembers = [];
      }
    },

    openAddTeamMemberModal() {
      this.editingTeamMember = false;
      this.teamMemberForm = { id: null, username: '', role: 'WAITER', contact: '', password: '', active: true };
      this.showTeamMemberModal = true;
    },

    editTeamMember(member) {
      this.editingTeamMember = true;
      this.teamMemberForm = {
        id: member.id,
        username: member.username,
        role: member.role,
        contact: member.contact || '',
        password: '',
        active: member.active !== undefined ? member.active : true
      };
      this.showTeamMemberModal = true;
    },

    closeTeamMemberModal() {
      this.showTeamMemberModal = false;
      this.editingTeamMember = false;
      this.teamMemberForm = { id: null, username: '', role: 'WAITER', contact: '', password: '', active: true };
    },

    closeTeamMemberModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeTeamMemberModal();
    },

    async saveTeamMember() {
      try {
        var url = this.editingTeamMember
          ? this.base_url + '/core/api/team/' + this.teamMemberForm.id
          : this.base_url + '/core/api/team/';

        var method = this.editingTeamMember ? 'put' : 'post';

        var data = {
          username: this.teamMemberForm.username,
          role: this.teamMemberForm.role,
          contact: this.teamMemberForm.contact,
          active: this.teamMemberForm.active !== undefined ? this.teamMemberForm.active : true
        };

        if (this.teamMemberForm.password && !this.editingTeamMember) {
          data.password = this.teamMemberForm.password;
        }

        if (this.editingTeamMember) {
          data.id = this.teamMemberForm.id;
        }

        var response = await axios[method](url, data, {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });

        if (response.ok) {
          this.showToast(
            this.editingTeamMember ? 'Team member updated successfully' : 'Team member added successfully',
            'success'
          );
          this.invalidateRelatedCaches('team');
          this.loadTeamMembers();
        } else {
          this.showToast(
            this.editingTeamMember ? 'Failed to update team member' : 'Failed to add team member',
            'error'
          );
        }
        this.closeTeamMemberModal();
      } catch (error) {
        console.error('Failed to save team member:', error);
        var message = (error.response && error.response.data && error.response.data.message) || 'Failed to save team member';
        this.showToast(message, 'error');
      }
    },

    async deleteTeamMember(member) {
      if (!confirm('Are you sure you want to remove ' + member.username + ' from the team? This cannot be undone.')) return;

      try {
        await axios.delete(this.base_url + '/core/api/team/' + member.id, {
          headers: { 'X-CSRFToken': this.getCSRFToken(), 'Content-Type': 'application/json' }
        });
        this.showToast('Team member removed successfully', 'success');
        this.loadTeamMembers();
      } catch (error) {
        console.error('Failed to delete team member:', error);
        this.showToast('Failed to remove team member. Please check your permissions.', 'error');
      }
    }
  }
};
