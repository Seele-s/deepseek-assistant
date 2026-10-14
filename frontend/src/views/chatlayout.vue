<template>
  <t-layout class="layout-container">
    <t-aside width="320px" class="sidebar">

      <t-button ghost block variant="dashed" size="large" class="new-chat-btn" @click="createNewChat">
        <template #icon><AddIcon /></template>
        新建对话
      </t-button>

      <div class="history-area">
        <div class="history-title">
          历史会话
          <span class="history-tip">双击标题可重命名</span>
        </div>

        <div
          v-for="sess in sessions"
          :key="sess.id"
          :class="['history-item', { active: currentSessionId === sess.id }]"
          @click="selectSession(sess.id)"
          @dblclick="startRename(sess)"
        >
          <!-- 重命名态：内联输入框 -->
          <input
            v-if="editingId === sess.id"
            ref="editInputEl"
            class="rename-input"
            v-model="editingTitle"
            maxlength="50"
            @click.stop
            @keydown.enter.prevent="saveRename(sess.id)"
            @keydown.esc.prevent="cancelRename"
            @blur="saveRename(sess.id)"
          />

          <!-- 正常态：标题 + 操作按钮 -->
          <template v-else>
            <span class="sess-title" :title="sess.title">{{ sess.title }}</span>
            <div class="item-actions">
              <t-button
                class="act-btn"
                variant="text" shape="square" size="medium"
                title="重命名"
                @click.stop="startRename(sess)"
              >
                <template #icon><Edit1Icon /></template>
              </t-button>
              <t-button
                class="act-btn del-btn"
                variant="text" shape="square" size="medium" theme="danger"
                title="删除"
                @click.stop="deleteSession(sess.id)"
              >
                <template #icon><DeleteIcon /></template>
              </t-button>
            </div>
          </template>
        </div>

        <div v-if="sessions.length === 0" class="history-empty">还没有会话，点上方新建</div>
      </div>

      <div class="user-footer">
        <div class="user-info">
          <t-avatar size="medium" style="background: #0052d9">{{ store.username ? store.username[0].toUpperCase() : 'U' }}</t-avatar>
          <span class="username">{{ store.username }}</span>
        </div>
        <t-button theme="danger" variant="text" shape="square" size="large" @click="doLogout">
            <template #icon><LogoutIcon /></template>
        </t-button>
      </div>
    </t-aside>

    <t-content class="content-area">
      <ChatWindow :session-id="currentSessionId" @refresh-list="fetchSessions" />
    </t-content>
  </t-layout>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';
import ChatWindow from '../components/ChatWindow.vue';
import { LogoutIcon, AddIcon, DeleteIcon, Edit1Icon } from 'tdesign-icons-vue-next';
import { MessagePlugin } from 'tdesign-vue-next';
import { api } from '../api';

const store = useUserStore();
const router = useRouter();
const sessions = ref([]);
const currentSessionId = ref(null);

// ---- 重命名状态 ----
const editingId = ref(null);
const editingTitle = ref('');
const editInputEl = ref(null);

const fetchSessions = async () => {
  try {
    sessions.value = await api.listSessions(store.token);
    // 进入页面时自动选中最近一次会话，避免右侧一直是空白
    if (!currentSessionId.value && sessions.value.length > 0) {
      currentSessionId.value = sessions.value[0].id;
    }
  } catch (e) {
    if (String(e.message).includes('401') || String(e.message).includes('登录')) {
      store.logout();
      router.push('/login');
    }
  }
};

// 不再弹窗让用户填标题：先建一个默认会话，发第一条消息时后端自动命名
const createNewChat = async () => {
  try {
    const newSession = await api.createSession(store.token);
    await fetchSessions();
    currentSessionId.value = newSession.id;
  } catch (e) { MessagePlugin.error('创建会话失败：' + e.message); }
};

const deleteSession = async (id) => {
  if (!confirm('确定要删除这个会话吗？删除后聊天记录无法恢复。')) return;
  try {
    await api.deleteSession(store.token, id);
    MessagePlugin.success('删除成功');
    if (currentSessionId.value === id) currentSessionId.value = null;
    await fetchSessions();   // 会自动切到剩下的最近一个会话
  } catch (e) { MessagePlugin.error('删除失败：' + e.message); }
};

// ---- 重命名 ----
const startRename = async (sess) => {
  editingId.value = sess.id;
  editingTitle.value = sess.title;
  await nextTick();
  const el = Array.isArray(editInputEl.value) ? editInputEl.value[0] : editInputEl.value;
  if (el && el.focus) { el.focus(); el.select && el.select(); }
};

const cancelRename = () => { editingId.value = null; editingTitle.value = ''; };

const saveRename = async (id) => {
  if (editingId.value !== id) return;      // 已保存过，避免 blur 重复触发
  const title = (editingTitle.value || '').trim();
  const sess = sessions.value.find((s) => s.id === id);
  editingId.value = null;
  if (!title) { MessagePlugin.warning('名称不能为空'); return; }
  if (!sess || title === sess.title) return;   // 没改就跳过

  try {
    await api.renameSession(store.token, id, title);
    sess.title = title;                        // 本地立即更新，无需整表刷新
    MessagePlugin.success('已重命名');
  } catch (e) {
    MessagePlugin.error('重命名失败：' + e.message);
    await fetchSessions();
  }
};

const selectSession = (id) => { currentSessionId.value = id; };
const doLogout = () => { store.logout(); router.push('/login'); };

onMounted(() => { fetchSessions(); });
</script>

<style scoped>
.layout-container { height: 100vh; overflow: hidden; }
.sidebar {
  background: #202123;
  color: #fff;
  padding: 20px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
}
.new-chat-btn { margin-bottom: 20px; border-radius: 8px; }
.history-area { flex: 1; overflow-y: auto; padding-right: 5px; }
.history-title {
  font-size: 13px; color: #8e8ea0; margin-bottom: 12px; font-weight: 500;
  display: flex; justify-content: space-between; align-items: center;
}
.history-tip { font-size: 11px; color: #5c5c66; font-weight: 400; }
.history-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px;
  font-size: 15px;
  color: #ececec; border-radius: 8px; cursor: pointer; margin-bottom: 4px;
}
.history-item:hover { background-color: #2a2b32; }
.history-item.active { background-color: #343541; }
.sess-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; margin-right: 8px; }
.item-actions { display: flex; gap: 2px; opacity: 0; transition: opacity 0.2s; }
.history-item:hover .item-actions { opacity: 1; }
.act-btn { color: #9aa0a6; }
.act-btn:hover { color: #fff; }
.del-btn { color: #ff4d4f; }
.history-empty { font-size: 13px; color: #6b6b73; text-align: center; padding: 24px 0; }
.rename-input {
  flex: 1; min-width: 0;
  background: #2f3037; color: #fff;
  border: 1px solid #4d71ff; border-radius: 6px;
  padding: 6px 10px; font-size: 15px; outline: none;
  font-family: inherit;
}
.user-footer {
  padding-top: 20px; margin-top: 10px;
  border-top: 1px solid #4d4d4f; display: flex; justify-content: space-between; align-items: center;
}
.user-info { display: flex; align-items: center; gap: 12px; font-size: 15px; font-weight: 500; min-width: 0; }
.username { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
