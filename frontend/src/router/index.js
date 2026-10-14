import { createRouter, createWebHistory } from 'vue-router';
import { useUserStore } from '../stores/user';
import Login from '../views/Login.vue';
import ChatLayout from '../views/ChatLayout.vue';

const routes = [
  { path: '/login', component: Login },
  { path: '/chat', component: ChatLayout, meta: { auth: true } },
  { path: '/', redirect: '/chat' }
];

const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach((to, from, next) => {
  const store = useUserStore();
  if (to.meta.auth && !store.token) next('/login');
  else next();
});
export default router;