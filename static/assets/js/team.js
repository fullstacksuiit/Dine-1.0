const apiUrl = window.location.origin + '/core/api/team/';
new Vue({
  el: '#team-app',
  delimiters: ['[[', ']]'],
  data: {
    team: [],
    showModal: false,
    showDeleteModal: false,
    editMode: false,
    modalMember: { id: null, username: '', role: '', contact: '', active: true },
    toast: { show: false, message: '', type: '' },
  },
  mounted() {
    axios.defaults.xsrfCookieName = 'csrftoken';
    axios.defaults.xsrfHeaderName = 'X-CSRFToken';
    axios.defaults.withCredentials = true;
    this.fetchTeam();
    if(window.feather) window.feather.replace();
  },
  updated() {
    if(window.feather) window.feather.replace();
  },
  methods: {
    showToast(message, type = 'success') {
      this.toast = { show: true, message, type };
      setTimeout(() => { this.toast.show = false; }, 3000);
    },
    fetchTeam() {
      axios.get(apiUrl)
        .then(res => { this.team = res.data; })
        .catch(() => this.showToast('Failed to load team', 'error'));
    },
    openAddModal() {
      this.editMode = false;
      this.modalMember = { id: null, username: '', role: 'WAITER', contact: '', active: true };
      this.showModal = true;
    },
    openEditModal(member) {
      this.editMode = true;
      this.modalMember = Object.assign({}, member);
      this.showModal = true;
    },
    openDeleteModal(member) {
      this.modalMember = Object.assign({}, member);
      this.showDeleteModal = true;
    },
    closeModal() {
      this.showModal = false;
      this.showDeleteModal = false;
    },
    addMember() {
      axios.post(apiUrl, this.modalMember)
        .then(() => {
          this.fetchTeam();
          this.closeModal();
          this.showToast('Member added successfully');
        })
        .catch(err => {
          this.showToast(err.response?.data?.error || 'Failed to add member', 'error');
        });
    },
    updateMember() {
      axios.put(apiUrl + this.modalMember.id, this.modalMember)
        .then(() => {
          this.fetchTeam();
          this.closeModal();
          this.showToast('Member updated successfully');
        })
        .catch(err => {
          this.showToast(err.response?.data?.error || 'Failed to update member', 'error');
        });
    },
    deleteMember() {
      axios.delete(apiUrl + this.modalMember.id)
        .then(() => {
          this.fetchTeam();
          this.closeModal();
          this.showToast('Member deleted successfully');
        })
        .catch(() => this.showToast('Failed to delete member', 'error'));
    },
  }
});
