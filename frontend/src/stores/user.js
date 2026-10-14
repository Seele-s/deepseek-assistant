import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '');
  const username = ref(localStorage.getItem('username') || '');

  function login(t, u) {
    token.value = t;
    username.value = u;
    localStorage.setItem('token', t);
    localStorage.setItem('username', u);
  }

  function logout() {
    token.value = '';
    username.value = '';
    localStorage.clear();
  }
  return { token, username, login, logout };
});