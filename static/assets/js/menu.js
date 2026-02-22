new Vue({
    el: "#menu",
    delimiters: ['[[', ']]'], // Change delimiters from {{ }} to [[ ]]
    data() {
    return {
      new_dish: { name: "", half_price: "0", full_price: "0", zomato_half_price: "0", zomato_full_price: "0", swiggy_half_price: "0", swiggy_full_price: "0", category: "" },
      update_dish: { id: "", name: "", course_name: "", restaurant_half_price: "0", restaurant_full_price: "0", zomato_half_price: "0", zomato_full_price: "0", swiggy_half_price: "0", swiggy_full_price: "0" },
      courses: [],
      dishes: [],
      total_dishes: 0,
      base_url: window.location.origin,
      orderedCourseIds: [],
      savingOrder: false,
      orderSaved: false,
      showOrderModal: false,
    };
  },
  mounted() {
    this.fetchCourses();
    this.fetchDishes();
    this.$nextTick(this.initSortable);
  },
  computed: {
    orderedCourses() {
      // Return courses in the order of orderedCourseIds, fallback to courses order
      if (!this.orderedCourseIds.length) return this.courses;
      const idMap = Object.fromEntries(this.courses.map(c => [c.id, c]));
      return this.orderedCourseIds.map(id => idMap[id]).filter(Boolean);
    },
    groupedDishes() {
      // Group dishes by course id, then output groups in the order of orderedCourses, but only include courses with dishes
      const groups = {};
      const idToName = {};
      (this.orderedCourses || []).forEach(course => {
        groups[course.id] = [];
        idToName[course.id] = course.name;
      });
      (this.dishes || []).forEach(dish => {
        const courseId = dish.course && dish.course.id ? dish.course.id : null;
        if (courseId && groups.hasOwnProperty(courseId)) {
          groups[courseId].push(dish);
        } else {
          if (!groups['no_course']) groups['no_course'] = [];
          groups['no_course'].push(dish);
          idToName['no_course'] = '—';
        }
      });
      // Only include courses with at least one dish
      const result = [];
      (this.orderedCourses || []).forEach(course => {
        if ((groups[course.id] || []).length > 0) {
          result.push([course.name, groups[course.id]]);
        }
      });
      if (groups['no_course'] && groups['no_course'].length > 0) {
        result.push(['—', groups['no_course']]);
      }
      return Object.fromEntries(result);
    },
  },
  methods: {
    fetchCourses() {
      axios.get('/sale/api/menu/')
        .then(response => {
          this.courses = response.data.courses || [];
          this.orderedCourseIds = response.data.ordering || [];
        })
        .catch(error => {
          console.error('Failed to fetch courses and ordering:', error);
        });
    },
    fetchDishes() {
      const url = `${this.base_url}/sale/api/dishes/`;
      axios.get(url)
        .then(response => {
          // Defensive: filter out null/undefined dishes and ensure course is always an object
          this.dishes = (response.data || []).map(dish => {
            if (!dish) return { name: '', course: { name: '—' } };
            if (!dish.course) dish.course = { name: '—' };
            return dish;
          });
          this.total_dishes = this.dishes.length;
        })
        .catch(error => {
          console.error('Failed to fetch dishes:', error);
        });
    },
    newDish() {
      this.new_dish = { name: "", half_price: "0", full_price: "0", zomato_half_price: "0", zomato_full_price: "0", swiggy_half_price: "0", swiggy_full_price: "0", category: "" };
    },
    createDish() {
      // Map Vue data to API fields
      const payload = {
        name: this.new_dish.name,
        restaurant_half_price: this.new_dish.half_price,
        restaurant_full_price: this.new_dish.full_price,
        zomato_half_price: this.new_dish.zomato_half_price,
        zomato_full_price: this.new_dish.zomato_full_price,
        swiggy_half_price: this.new_dish.swiggy_half_price,
        swiggy_full_price: this.new_dish.swiggy_full_price,
        course_name: this.new_dish.category
      };
      const url = `${this.base_url}/sale/api/dishes/`;
      axios.post(url, payload, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(response => {
          this.fetchDishes();
          this.showToast('Dish added successfully!', 'success');
          this.fetchDishes();
          this.fetchCourses();
          this.newDish(); // reset form
        })
        .catch(error => {
          this.showToast('Failed to add dish. Please check your input and try again.', 'danger');
        });
    },
    openUpdateDishModal(dish) {
      console.log('Opening update modal for dish:', dish);
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
      document.getElementById('updateDishModal').style.display = 'flex';
    },
    closeUpdateDishModal() {
      // Close the modal and reset the update dish data
      this.update_dish = { id: "", name: "", course_name: "", restaurant_half_price: "0", restaurant_full_price: "0", zomato_half_price: "0", zomato_full_price: "0", swiggy_half_price: "0", swiggy_full_price: "0" };
      document.getElementById('updateDishModal').style.display = 'none';
    },
    submitUpdateDish() {
      const payload = {
        name: this.update_dish.name,
        restaurant_half_price: this.update_dish.restaurant_half_price,
        restaurant_full_price: this.update_dish.restaurant_full_price,
        swiggy_half_price: this.update_dish.swiggy_half_price,
        swiggy_full_price: this.update_dish.swiggy_full_price,
        zomato_half_price: this.update_dish.zomato_half_price,
        zomato_full_price: this.update_dish.zomato_full_price,
        course_name: this.update_dish.course_name
      };
      const url = `${this.base_url}/sale/api/dishes/${this.update_dish.id}`;
      axios.put(url, payload, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(response => {
          this.showToast('Dish updated successfully!', 'success');
          this.fetchDishes();
          this.fetchCourses();
          this.closeUpdateDishModal();
        })
        .catch(error => {
          this.showToast('Failed to update dish. Please check your input and try again.', 'danger');
        });
    },
    initSortable() {
      this.$nextTick(() => {
        if (window.Sortable && document.getElementById('course-order-list')) {
          if (this._sortableInstance) this._sortableInstance.destroy();
          this._sortableInstance = Sortable.create(document.getElementById('course-order-list'), {
            animation: 150,
            onEnd: evt => {
              const newOrder = [];
              document.querySelectorAll('#course-order-list li').forEach(li => {
                const idx = li.getAttribute('data-vue-key') || li.getAttribute('key');
                const course = this.orderedCourses[idx] || this.courses[idx];
                if (course) newOrder.push(course.id);
              });
              this.orderedCourseIds = newOrder;
            }
          });
        }
      });
    },
    saveCourseOrder() {
      this.savingOrder = true;
      this.orderSaved = false;
      // Get the current order of course IDs from the DOM (dragged order)
      const liNodes = document.querySelectorAll('#course-order-list li');
      // Each li has a Vue :key set to course.id, which is rendered as an attribute 'data-key' by Vue
      const newOrder = Array.from(liNodes).map(li => li.getAttribute('data-key') || li.getAttribute('key') || li.getAttribute('data-vue-key'));
      // Fallback: if newOrder is empty, use this.orderedCourses
      const ordering = newOrder.filter(Boolean).length ? newOrder.filter(Boolean) : this.orderedCourses.map(c => c.id);
      axios.post('/sale/api/menu/', { ordering }, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(() => {
          this.savingOrder = false;
          this.orderSaved = true;
          this.showToast('Menu order saved successfully!', 'success');
          setTimeout(() => { this.orderSaved = false; this.showOrderModal = false; }, 1200);
          this.fetchDishes();
          this.fetchCourses();
          // Remove direct DOM manipulation for modal closing
          document.getElementById('showOrderModal').style.display = 'none';
        })
        .catch(() => {
          this.savingOrder = false;
        });
    },
    downloadPublicMenuQR() {
      // Use the backend QR API for the authenticated QR code
      const link = document.createElement('a');
      link.href = '/sale/api/public-menu-qr/';
      link.download = 'public-menu-qr.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    getCSRFToken() {
      const name = 'csrftoken';
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        let cookie = cookies[i].trim();
        if (cookie.startsWith(name + '=')) {
          return decodeURIComponent(cookie.substring(name.length + 1));
        }
      }
      return '';
    },
    deleteDish(dishId) {
      if (!confirm('Are you sure you want to delete this dish?')) return;
      const url = `${this.base_url}/sale/api/dishes/${dishId}`;
      axios.delete(url, {
        headers: { 'X-CSRFTOKEN': this.getCSRFToken() }
      })
        .then(() => {
          this.showToast('Dish deleted successfully!', 'success');
          this.fetchDishes();
          this.fetchCourses();
        })
        .catch(() => {
          this.showToast('Failed to delete dish. Please try again.', 'danger');
        });
    },
    showToast(message, type = 'success') {
      // Remove any existing toast
      const oldToast = document.getElementById('custom-toast');
      if (oldToast) oldToast.remove();
      // Create toast element
      const toast = document.createElement('div');
      toast.id = 'custom-toast';
      toast.style.position = 'fixed';
      toast.style.bottom = '32px';
      toast.style.right = '32px';
      toast.style.zIndex = 9999;
      toast.style.background = type === 'success' ? '#4caf50' : (type === 'danger' ? '#e53935' : '#333');
      toast.style.color = '#fff';
      toast.style.padding = '14px 28px';
      toast.style.borderRadius = '8px';
      toast.style.fontSize = '1rem';
      toast.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
      toast.innerText = message;
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.remove();
      }, 3000);
    },
  }
});