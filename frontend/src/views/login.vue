<template>
  <div class="login-container">
    <div class="login-wrapper">
      
      <div class="brand-header">
        <div class="logo-placeholder">
            <t-icon name="chat-bubble-smile" size="40px" style="color: #4d71ff" />
        </div>
        <h1 class="brand-title">DeepSeek</h1>
        <p class="brand-subtitle">探索未知的智能世界</p>
      </div>

      <t-card :bordered="false" class="auth-card">
        <t-tabs v-model="tab" size="large">
          
          <t-tab-panel value="login" label="账号登录">
            <div class="form-content">
              <t-input 
                v-model="form.username" 
                placeholder="请输入用户名 / 手机号" 
                size="large" 
                clearable
              >
                <template #prefix-icon><t-icon name="user" /></template>
              </t-input>
              
              <t-input 
                v-model="form.password" 
                type="password" 
                placeholder="请输入密码" 
                size="large"
                clearable
              >
                <template #prefix-icon><t-icon name="lock-on" /></template>
              </t-input>

              <t-button block theme="primary" size="large" class="submit-btn" @click="doLogin" :loading="loading">
                登 录
              </t-button>
              
              <div class="extra-links">
                <span>忘记密码?</span>
              </div>
            </div>
          </t-tab-panel>

          <t-tab-panel value="register" label="注册新账号">
            <div class="form-content">
              <t-input v-model="reg.username" placeholder="设置您的用户名" size="large">
                <template #prefix-icon><t-icon name="user-add" /></template>
              </t-input>
              
              <t-input v-model="reg.password" type="password" placeholder="设置登录密码" size="large">
                <template #prefix-icon><t-icon name="lock-on" /></template>
              </t-input>

              <t-button block theme="default" variant="outline" size="large" class="submit-btn" @click="doReg" :loading="loading">
                立即注册
              </t-button>
            </div>
          </t-tab-panel>

        </t-tabs>
      </t-card>

      <div class="footer-copyright">
        © 2024 DeepSeek Clone Project. All Rights Reserved.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';
import { MessagePlugin } from 'tdesign-vue-next';
import { api } from '../api';

const router = useRouter();
const store = useUserStore();
const tab = ref('login');
const loading = ref(false);
const form = reactive({ username: '', password: '' });
const reg = reactive({ username: '', password: '' });

const doLogin = async () => {
  loading.value = true;
  const data = new URLSearchParams();
  data.append('username', form.username);
  data.append('password', form.password);
  
  try {
    const json = await api.login(form.username, form.password);
    store.login(json.access_token, form.username);
    MessagePlugin.success('登录成功，正在跳转...');
    setTimeout(() => {
        router.push('/chat');
    }, 500);
  } catch(e) { MessagePlugin.error(e.message); } 
  finally { loading.value = false; }
};

const doReg = async () => {
  loading.value = true;
  try {
    await api.register(reg.username, reg.password);
    MessagePlugin.success('注册成功，请切换到登录页进行登录');
    tab.value = 'login';
  } catch(e) { MessagePlugin.error(e.message); }
  finally { loading.value = false; }
};
</script>

<style scoped>
/* 背景：使用深色渐变或灰白色，更像 SaaS 软件 */
.login-container { 
  min-height: 100vh; 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  background-color: #f2f3f5;
  background-image: 
    radial-gradient(#e3e3e3 1px, transparent 1px),
    radial-gradient(#e3e3e3 1px, transparent 1px);
  background-size: 20px 20px;
  background-position: 0 0, 10px 10px;
}

.login-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

/* 顶部品牌区 */
.brand-header {
  text-align: center;
  margin-bottom: 40px;
}
.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: #181818;
  margin: 10px 0 5px;
  letter-spacing: 1px;
}
.brand-subtitle {
  font-size: 14px;
  color: #888;
  margin: 0;
}

/* 卡片样式：加宽、加阴影 */
.auth-card { 
  width: 480px; /* 【关键】宽度改大了 */
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.08); /* 悬浮感阴影 */
  overflow: hidden;
}

/* 调整卡片内部间距 */
:deep(.t-card__body) {
  padding: 40px !important; /* 【关键】内边距改大了 */
}

/* 表单间距 */
.form-content {
  margin-top: 25px;
  display: flex;
  flex-direction: column;
  gap: 20px; /* 输入框之间的距离 */
}

/* 按钮样式微调 */
.submit-btn {
  margin-top: 10px;
  height: 48px; /* 按钮更高 */
  font-size: 16px;
  font-weight: 500;
  border-radius: 6px;
}

.extra-links {
  display: flex;
  justify-content: flex-end;
  font-size: 13px;
  color: #666;
  margin-top: -10px;
  cursor: pointer;
}
.extra-links:hover {
  color: #0052d9;
}

.footer-copyright {
  margin-top: 40px;
  color: #bbb;
  font-size: 12px;
}
</style>