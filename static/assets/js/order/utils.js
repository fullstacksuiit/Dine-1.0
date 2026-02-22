window.DinePay = window.DinePay || {};

DinePay.UtilsMixin = {
  methods: {
    showToast(message, type = 'success') {
      var old = document.getElementById('custom-toast');
      if (old) old.remove();

      var toast = document.createElement('div');
      toast.id = 'custom-toast';
      toast.style.position = 'fixed';
      toast.style.bottom = '32px';
      toast.style.right = '32px';
      toast.style.zIndex = 9999;

      var backgroundColor;
      switch (type) {
        case 'success': backgroundColor = '#4caf50'; break;
        case 'danger':  backgroundColor = '#e53935'; break;
        case 'info':    backgroundColor = '#2196f3'; break;
        default:        backgroundColor = '#333';
      }

      toast.style.background = backgroundColor;
      toast.style.color = '#fff';
      toast.style.padding = '14px 28px';
      toast.style.borderRadius = '8px';
      toast.style.fontSize = '1rem';
      toast.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
      toast.innerText = message;
      document.body.appendChild(toast);

      var timeout = type === 'info' ? 5000 : 3000;
      setTimeout(function () {
        if (toast.parentNode) toast.remove();
      }, timeout);
    },

    getISTDate() {
      var now = new Date();
      var utc = now.getTime() + (now.getTimezoneOffset() * 60000);
      var istOffset = 5.5 * 60 * 60000;
      return new Date(utc + istOffset);
    },

    formatDate(dateString) {
      if (!dateString) return '';
      var date = new Date(dateString);
      var utc = date.getTime() + (date.getTimezoneOffset() * 60000);
      var istOffset = 5.5 * 60 * 60000;
      var istDate = new Date(utc + istOffset);
      var day = String(istDate.getDate()).padStart(2, '0');
      var month = String(istDate.getMonth() + 1).padStart(2, '0');
      var year = istDate.getFullYear();
      return day + '/' + month + '/' + year;
    },

    formatTime(dateString) {
      if (!dateString) return '';
      var date = new Date(dateString);
      var utc = date.getTime() + (date.getTimezoneOffset() * 60000);
      var istOffset = 5.5 * 60 * 60000;
      var istDate = new Date(utc + istOffset);
      var hours = String(istDate.getHours()).padStart(2, '0');
      var minutes = String(istDate.getMinutes()).padStart(2, '0');
      return hours + ':' + minutes;
    },

    formatKotTime(timeString) {
      if (!timeString) return '';
      var time = new Date('2000-01-01T' + timeString);
      return time.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    },

    formatKotDateTime(dateString) {
      if (!dateString) return '';
      var date = new Date(dateString);
      var dateStr = date.toLocaleDateString('en-GB');
      var timeStr = date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
      return dateStr + ' - ' + timeStr;
    },

    timeAgo(dateString) {
      if (!dateString) return '';
      var now = new Date();
      var then = new Date(dateString);
      var seconds = Math.floor((now - then) / 1000);

      if (seconds < 60) return 'just now';

      var intervals = [
        { label: 'year', seconds: 31536000 },
        { label: 'month', seconds: 2592000 },
        { label: 'day', seconds: 86400 },
        { label: 'hour', seconds: 3600 },
        { label: 'minute', seconds: 60 }
      ];

      for (var i = 0; i < intervals.length; i++) {
        var count = Math.floor(seconds / intervals[i].seconds);
        if (count >= 1) {
          return count + ' ' + intervals[i].label + (count > 1 ? 's' : '') + ' ago';
        }
      }
      return 'just now';
    },

    formatTableDuration(dateString) {
      if (!dateString) return '0m';
      var now = new Date();
      var start = new Date(dateString);
      var seconds = Math.floor((now - start) / 1000);

      if (seconds < 60) return '< 1m';

      var minutes = Math.floor(seconds / 60);
      if (minutes < 60) return minutes + 'm';

      var hours = Math.floor(minutes / 60);
      var remainingMinutes = minutes % 60;

      if (hours >= 24) {
        var days = Math.floor(hours / 24);
        return days + 'd';
      }

      return remainingMinutes > 0 ? hours + 'h ' + remainingMinutes + 'm' : hours + 'h';
    },

    getCsrfToken() {
      var getCookie = function (name) {
        var cookies = document.cookie ? document.cookie.split(';') : [];
        for (var i = 0; i < cookies.length; i++) {
          var cookie = cookies[i].trim();
          if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.substring(name.length + 1));
          }
        }
        return null;
      };
      return getCookie('csrftoken');
    },

    getCSRFToken() {
      return this.getCsrfToken();
    },

    formatCurrency(amount) {
      if (amount == null || amount == undefined) return '0';
      return Number(amount).toLocaleString('en-IN');
    }
  }
};
