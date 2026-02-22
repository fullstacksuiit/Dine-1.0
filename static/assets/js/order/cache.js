window.DinePay = window.DinePay || {};

DinePay.CacheMixin = {
  data: function () {
    return {
      cache: {
        currentUser:          { data: null, timestamp: null, ttl: 600000 },
        menuData:             { data: null, timestamp: null, ttl: 300000 },
        activeTables:         { data: null, timestamp: null, ttl: 120000 },
        activeDineInKots:     { data: null, timestamp: null, ttl: 120000 },
        activeTakeawayOrders: { data: null, timestamp: null, ttl: 120000 },
        teamMembers:          { data: null, timestamp: null, ttl: 120000 },
        billingHistory:       { data: null, timestamp: null, ttl: 120000 },
        popularDishes:        { data: null, timestamp: null, ttl: 1800000 }
      }
    };
  },

  methods: {
    isCacheValid: function (cacheKey) {
      var cacheEntry = this.cache[cacheKey];
      if (!cacheEntry || !cacheEntry.data || !cacheEntry.timestamp) return false;
      var now = Date.now();
      var isValid = (now - cacheEntry.timestamp) < cacheEntry.ttl;
      if (!isValid) this.invalidateCache(cacheKey);
      return isValid;
    },

    invalidateCache: function (cacheKey) {
      if (this.cache[cacheKey]) {
        this.cache[cacheKey].data = null;
        this.cache[cacheKey].timestamp = null;
      }
    },

    setCache: function (cacheKey, data) {
      if (this.cache[cacheKey]) {
        this.cache[cacheKey].data = data;
        this.cache[cacheKey].timestamp = Date.now();
      }
    },

    getCache: function (cacheKey) {
      if (this.isCacheValid(cacheKey)) return this.cache[cacheKey].data;
      return null;
    },

    invalidateRelatedCaches: function (operation) {
      switch (operation) {
        case 'menu':
          this.invalidateCache('menuData');
          break;
        case 'user':
          this.invalidateCache('currentUser');
          this.invalidateCache('teamMembers');
          break;
        case 'order':
          this.invalidateCache('activeTables');
          this.invalidateCache('activeDineInKots');
          this.invalidateCache('popularDishes');
          break;
        case 'takeaway':
          this.invalidateCache('activeTakeawayOrders');
          this.invalidateCache('popularDishes');
          break;
        case 'team':
          this.invalidateCache('teamMembers');
          break;
        case 'billing':
          this.invalidateCache('billingHistory');
          this.invalidateCache('activeTables');
          break;
      }
    },

    invalidateAllCaches: function () {
      var self = this;
      Object.keys(this.cache).forEach(function (key) {
        self.invalidateCache(key);
      });
    }
  }
};
