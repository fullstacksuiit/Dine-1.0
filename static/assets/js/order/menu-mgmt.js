window.DinePay = window.DinePay || {};

DinePay.MenuMgmtMixin = {
  data: function () {
    return {
      dishes: [],
      courses: [],
      orderedCourseIds: [],
      popularDishes: [],
      total_dishes: 0,
      showMenuModal: false,
      showAddDishModal: false,
      showUpdateDishModal: false,
      showCourseOrderModal: false,
      new_dish: {
        name: '',
        half_price: '0',
        full_price: '0',
        zomato_half_price: '0',
        zomato_full_price: '0',
        swiggy_half_price: '0',
        swiggy_full_price: '0',
        category: ''
      },
      update_dish: {
        id: '',
        name: '',
        course_name: '',
        restaurant_half_price: '0',
        restaurant_full_price: '0',
        zomato_half_price: '0',
        zomato_full_price: '0',
        swiggy_half_price: '0',
        swiggy_full_price: '0'
      },
      menuColumnSaveStatus: false,
      savingOrder: false,
      orderSaved: false
    };
  },

  computed: {
    orderedCourses: function () {
      if (!this.orderedCourseIds.length) return this.courses;
      var idMap = {};
      this.courses.forEach(function (c) { idMap[c.id] = c; });
      return this.orderedCourseIds.map(function (id) { return idMap[id]; }).filter(Boolean);
    },

    groupedDishes: function () {
      var groups = {};
      var idToName = {};
      var self = this;

      (this.orderedCourses || []).forEach(function (course) {
        groups[course.id] = [];
        idToName[course.id] = course.name || course.course_name || ('Course ' + course.id) || 'Unnamed Course';
      });

      (this.dishes || []).forEach(function (dish) {
        var courseId = dish.course && dish.course.id ? dish.course.id : null;
        if (courseId && groups.hasOwnProperty(courseId)) {
          groups[courseId].push(dish);
        } else {
          if (!groups['no_course']) groups['no_course'] = [];
          groups['no_course'].push(dish);
          idToName['no_course'] = 'Uncategorized';
        }
      });

      var result = [];
      (this.orderedCourses || []).forEach(function (course) {
        if ((groups[course.id] || []).length > 0) {
          var courseName = course.name || course.course_name || ('Course ' + course.id) || 'Unnamed Course';
          result.push([courseName, groups[course.id]]);
        }
      });
      if (groups['no_course'] && groups['no_course'].length > 0) {
        result.push(['Uncategorized', groups['no_course']]);
      }
      return Object.fromEntries(result);
    }
  },

  methods: {
    fetchCourses() {
      var self = this;
      if (this.isCacheValid('menuData')) {
        var menuData = this.getCache('menuData');
        this.courses = menuData.courses || [];
        this.orderedCourseIds = menuData.ordering || [];
        return;
      }

      axios.get('/sale/api/menu/')
        .then(function (response) {
          self.courses = response.data.courses || [];
          self.orderedCourseIds = response.data.ordering || [];
          self.updateMenuCache();
        })
        .catch(function (error) {
          console.error('Failed to fetch courses and ordering:', error);
        });
    },

    fetchDishes() {
      var self = this;
      if (this.isCacheValid('menuData')) {
        var menuData = this.getCache('menuData');
        this.dishes = menuData.dishes || [];
        this.total_dishes = this.dishes.length;
        return;
      }

      axios.get(this.base_url + '/sale/api/dishes/')
        .then(function (response) {
          self.dishes = (response.data || []).map(function (dish) {
            if (!dish) return { name: '', course: { name: '\u2014' } };
            if (!dish.course) dish.course = { name: '\u2014' };
            return dish;
          });
          self.total_dishes = self.dishes.length;
          self.updateMenuCache();
        })
        .catch(function (error) {
          console.error('Failed to fetch dishes:', error);
        });
    },

    async fetchMenuData() {
      if (this.isCacheValid('menuData')) {
        var menuData = this.getCache('menuData');
        this.courses = menuData.courses || [];
        this.dishes = menuData.dishes || [];
        this.orderedCourseIds = menuData.ordering || [];
        this.total_dishes = this.dishes.length;
        this.fetchPopularDishes();
        return;
      }

      try {
        var results = await Promise.all([
          axios.get('/sale/api/menu/'),
          axios.get(this.base_url + '/sale/api/dishes/')
        ]);

        this.courses = results[0].data.courses || [];
        this.orderedCourseIds = results[0].data.ordering || [];

        this.dishes = (results[1].data || []).map(function (dish) {
          if (!dish) return { name: '', course: { name: '\u2014' } };
          if (!dish.course) dish.course = { name: '\u2014' };
          return dish;
        });
        this.total_dishes = this.dishes.length;

        this.setCache('menuData', {
          courses: this.courses,
          dishes: this.dishes,
          ordering: this.orderedCourseIds
        });

        this.fetchPopularDishes();
      } catch (error) {
        console.error('Failed to fetch menu data:', error);
        this.showToast('Failed to load menu data. Please try again.', 'error');
      }
    },

    updateMenuCache() {
      if (this.courses.length || this.dishes.length) {
        this.setCache('menuData', {
          courses: this.courses,
          dishes: this.dishes,
          ordering: this.orderedCourseIds
        });
      }
    },

    async fetchPopularDishes() {
      var cached = this.getCache('popularDishes');
      if (cached) {
        this.popularDishes = cached;
        return;
      }

      try {
        var self = this;
        var response = await axios.get(this.base_url + '/sale/api/dishes/popular/');
        var popularIds = (response.data || []).map(function (item) { return String(item.dish_id); });

        this.popularDishes = popularIds
          .map(function (id) { return self.dishes.find(function (d) { return String(d.id) === id; }); })
          .filter(Boolean);

        this.setCache('popularDishes', this.popularDishes);
      } catch (error) {
        console.error('Failed to fetch popular dishes:', error);
        this.popularDishes = [];
      }
    },

    quickAddDish(dish) {
      var existing = this.currentOrder.find(function (item) { return item.id === dish.id; });
      if (existing) {
        existing.quantity = Math.min((existing.quantity || 1) + 1, 99);
        return;
      }

      if (this.currentOrder.length === 1 && !this.currentOrder[0].name.trim() && !this.currentOrder[0].id) {
        this.currentOrder.splice(0, 1);
      }

      var newItem = {
        name: dish.name,
        quantity: 1,
        size: 'full',
        id: dish.id,
        price: 0,
        notes: '',
        showSuggestions: false,
        suggestions: [],
        selectedSuggestion: 0
      };
      this.updateItemPrice(newItem, dish);
      this.currentOrder.push(newItem);
      this.addItem();
    },

    openAddDishModal() {
      this.new_dish = {
        name: '',
        half_price: '0',
        full_price: '0',
        zomato_half_price: '0',
        zomato_full_price: '0',
        swiggy_half_price: '0',
        swiggy_full_price: '0',
        category: ''
      };
      if (!this.isCacheValid('courses')) this.fetchCourses();
      this.showAddDishModal = true;
    },

    closeAddDishModal() {
      this.showAddDishModal = false;
      this.setActiveTab('menu');
    },

    closeAddDishModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeAddDishModal();
    },

    createDish() {
      var self = this;
      var payload = {
        name: this.new_dish.name,
        restaurant_half_price: this.new_dish.half_price,
        restaurant_full_price: this.new_dish.full_price,
        zomato_half_price: this.new_dish.zomato_half_price,
        zomato_full_price: this.new_dish.zomato_full_price,
        swiggy_half_price: this.new_dish.swiggy_half_price,
        swiggy_full_price: this.new_dish.swiggy_full_price,
        course_name: this.new_dish.category
      };

      axios.post(this.base_url + '/sale/api/dishes/', payload, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(function (response) {
          self.invalidateRelatedCaches('menu');
          self.dishes.push(response.data);
          self.total_dishes = self.dishes.length;
          self.showToast('Dish added successfully!', 'success');
          self.closeAddDishModal();
        })
        .catch(function () {
          self.showToast('Failed to add dish. Please check your input and try again.', 'danger');
        });
    },

    openUpdateDishModal(dish) {
      this.update_dish = {
        id: dish.id,
        name: dish.name,
        course_name: dish.course && dish.course.name ? dish.course.name : '',
        restaurant_half_price: dish.restaurant_half_price,
        restaurant_full_price: dish.restaurant_full_price,
        swiggy_half_price: dish.swiggy_half_price,
        swiggy_full_price: dish.swiggy_full_price,
        zomato_half_price: dish.zomato_half_price,
        zomato_full_price: dish.zomato_full_price
      };
      this.fetchCourses();
      this.showUpdateDishModal = true;
    },

    closeUpdateDishModal() {
      this.showUpdateDishModal = false;
      this.update_dish = {
        id: '',
        name: '',
        course_name: '',
        restaurant_half_price: '0',
        restaurant_full_price: '0',
        zomato_half_price: '0',
        zomato_full_price: '0',
        swiggy_half_price: '0',
        swiggy_full_price: '0'
      };
      this.setActiveTab('menu');
    },

    closeUpdateDishModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeUpdateDishModal();
    },

    submitUpdateDish() {
      var self = this;
      var payload = {
        name: this.update_dish.name,
        restaurant_half_price: this.update_dish.restaurant_half_price,
        restaurant_full_price: this.update_dish.restaurant_full_price,
        swiggy_half_price: this.update_dish.swiggy_half_price,
        swiggy_full_price: this.update_dish.swiggy_full_price,
        zomato_half_price: this.update_dish.zomato_half_price,
        zomato_full_price: this.update_dish.zomato_full_price,
        course_name: this.update_dish.course_name
      };

      axios.put(this.base_url + '/sale/api/dishes/' + this.update_dish.id, payload, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(function (response) {
          self.showToast('Dish updated successfully!', 'success');
          self.invalidateRelatedCaches('menu');
          var dishIndex = self.dishes.findIndex(function (d) { return d.id === self.update_dish.id; });
          if (dishIndex !== -1) self.dishes[dishIndex] = response.data;
          self.closeUpdateDishModal();
        })
        .catch(function () {
          self.showToast('Failed to update dish. Please check your input and try again.', 'danger');
        });
    },

    deleteDish(dishId) {
      if (!confirm('Are you sure you want to delete this dish?')) return;
      var self = this;

      axios.delete(this.base_url + '/sale/api/dishes/' + dishId, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(function () {
          self.showToast('Dish deleted successfully!', 'success');
          self.invalidateRelatedCaches('menu');
          self.dishes = self.dishes.filter(function (dish) { return dish.id !== dishId; });
          self.total_dishes = self.dishes.length;
        })
        .catch(function () {
          self.showToast('Failed to delete dish. Please try again.', 'danger');
        });
    },

    openCourseOrderModal() {
      this.showCourseOrderModal = true;
      this.$nextTick(function () { this.initSortable(); }.bind(this));
    },

    closeCourseOrderModal() {
      this.showCourseOrderModal = false;
    },

    closeCourseOrderModalOnOverlay(event) {
      if (event.target === event.currentTarget) this.closeCourseOrderModal();
    },

    initSortable() {
      var self = this;
      this.$nextTick(function () {
        if (window.Sortable && document.getElementById('course-order-list')) {
          if (self._sortableInstance) self._sortableInstance.destroy();
          self._sortableInstance = Sortable.create(document.getElementById('course-order-list'), {
            animation: 150,
            onEnd: function () {
              var newOrder = [];
              document.querySelectorAll('#course-order-list li').forEach(function (li) {
                var courseId = li.getAttribute('data-key');
                if (courseId) newOrder.push(parseInt(courseId));
              });
              self.orderedCourseIds = newOrder;
            }
          });
        }
      });
    },

    saveCourseOrder() {
      var self = this;
      this.savingOrder = true;
      this.orderSaved = false;

      var liNodes = document.querySelectorAll('#course-order-list li');
      var newOrder = Array.from(liNodes).map(function (li) { return li.getAttribute('data-key'); }).filter(Boolean);
      var ordering = newOrder.length ? newOrder : this.orderedCourses.map(function (c) { return c.id; });

      axios.post('/sale/api/menu/', { ordering: ordering }, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(function () {
          self.savingOrder = false;
          self.orderSaved = true;
          self.showToast('Menu order saved successfully!', 'success');
          setTimeout(function () {
            self.orderSaved = false;
            self.closeCourseOrderModal();
          }, 1200);
          self.fetchDishes();
          self.fetchCourses();
        })
        .catch(function () {
          self.savingOrder = false;
          self.showToast('Failed to save order. Please try again.', 'danger');
        });
    },

    viewPublicMenu() {
      window.open('/sale/public/menu/' + this.currentUser.restaurant.id, '_blank');
    },

    downloadPublicMenuQR() {
      var link = document.createElement('a');
      link.href = '/sale/api/public-menu-qr/';
      link.download = 'public-menu-qr.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      this.showToast('QR Code downloaded!', 'success');
    },

    exportMenu() {
      var link = document.createElement('a');
      link.href = '/sale/api/dishes/download/';
      link.download = 'dishes_menu.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      this.showToast('Menu exported successfully!', 'success');
    },

    importMenu(event) {
      var self = this;
      var file = event.target.files[0];
      if (!file) return;

      if (!file.name.toLowerCase().endsWith('.xlsx')) {
        this.showToast('Please select a valid Excel (.xlsx) file', 'danger');
        return;
      }

      var formData = new FormData();
      formData.append('file', file);

      this.showToast('Importing menu... Please wait.', 'info');

      axios.post('/sale/api/dishes/upload/', formData, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken(), 'Content-Type': 'multipart/form-data' }
      })
        .then(function () {
          self.showToast('Menu imported successfully!', 'success');
          self.fetchDishes();
          self.fetchCourses();
          if (self.$refs.menuImportFile) self.$refs.menuImportFile.value = '';
        })
        .catch(function (error) {
          console.error('Import error:', error);
          self.showToast('Failed to import menu. Please check the file format.', 'danger');
          if (self.$refs.menuImportFile) self.$refs.menuImportFile.value = '';
        });
    },

    filterMenuTable() {
      var input = document.getElementById('menuSearchInput');
      if (!input) return;

      var searchValue = input.value.toUpperCase();
      var table = document.getElementById('menuTable');
      if (!table) return;

      var tr = table.getElementsByTagName('tr');

      function getShortCode(str) {
        return str.split(/\s+/).map(function (w) { return w[0] ? w[0].toUpperCase() : ''; }).join('');
      }

      for (var i = 1; i < tr.length; i++) {
        var row = tr[i];
        if (row.classList.contains('course-header')) {
          row.style.display = '';
          continue;
        }

        var nameTd = row.querySelector('td[data-col="name"]');
        var idTd = row.querySelector('td[data-col="id"]');
        var nameText = nameTd ? nameTd.innerText.toUpperCase() : '';
        var idText = idTd ? idTd.innerText.toUpperCase() : '';
        var shortCode = getShortCode(nameText);

        var match = nameText.indexOf(searchValue) > -1 ||
                    idText.indexOf(searchValue) > -1 ||
                    shortCode.indexOf(searchValue) > -1;

        row.style.display = match ? '' : 'none';
      }
    },

    applyMenuColumnPrefs() {
      document.querySelectorAll('.menu-col-toggle').forEach(function (checkbox) {
        var col = checkbox.value;
        var checked = checkbox.checked;
        document.querySelectorAll('th[data-col="' + col + '"], td[data-col="' + col + '"]').forEach(function (el) {
          el.style.display = checked ? '' : 'none';
        });
      });
    },

    saveMenuColumnPrefs() {
      var prefs = {};
      document.querySelectorAll('.menu-col-toggle').forEach(function (checkbox) {
        prefs[checkbox.value] = checkbox.checked;
      });
      localStorage.setItem('menu_column_prefs', JSON.stringify(prefs));
      this.menuColumnSaveStatus = true;
      var self = this;
      setTimeout(function () { self.menuColumnSaveStatus = false; }, 1200);
    }
  }
};
