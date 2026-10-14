import { createApp } from 'vue';
import { createPinia } from 'pinia';
import TDesign from 'tdesign-vue-next';
import App from './App.vue';
import router from './router';
import 'tdesign-vue-next/es/style/index.css';
import 'highlight.js/styles/atom-one-dark.css'; // 代码高亮样式
import './style.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(TDesign);
app.mount('#app');