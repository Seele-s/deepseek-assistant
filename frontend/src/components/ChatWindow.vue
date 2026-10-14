<template>
  <div class="fixed-width-container">
    <template v-if="sessionId">

      <div class="chat-history" ref="box" @click="onChatClick">
        <div v-if="list.length === 0" class="chat-start-tip-container">
          <div class="chat-start-tip-content">
            <t-icon name="chat" size="24px" />
            <span>DeepSeek 助手已就绪，输入问题开始对话</span>
          </div>
        </div>

        <div v-for="item in list" :key="item.id" :class="['msg-row', item.role]">
          <t-avatar v-if="item.role === 'user'" size="medium" style="background:#4d71ff">U</t-avatar>
          <t-avatar v-else size="medium" style="background:#eef2ff">
            <t-icon name="chat-bubble-smile" size="20px" style="color:#4d71ff" />
          </t-avatar>

          <div class="bubble">
            <t-loading v-if="item.loading && !item.reasoning && !item.content" size="small"/>

            <div v-if="item.reasoning" class="reasoning-box">
              <div class="reasoning-title"><t-icon name="lightbulb" size="12px" /> 深度思考过程</div>
              <div class="reasoning-content markdown-body" v-html="renderMd(item.reasoning)"></div>
            </div>

            <div v-if="item.content" class="markdown-body" v-html="renderMd(item.content)"></div>

            <div v-if="item.error" class="error-tip">
              <t-icon name="error-circle" /> {{ item.error }}
            </div>
          </div>
        </div>
      </div>

      <div class="footer-input-area">
        <div class="input-shadow-box">
          <div v-if="uploadedFile" class="file-preview">
            <t-icon name="file" /> <span class="filename">{{ uploadedFile.originalName }}</span>
            <t-icon name="close" class="close-btn" @click="clearFile" />
          </div>

          <div class="toolbar">
            <div :class="['tool-btn', 'reasoning-btn', { active: isReasoning }]" @click="toggleReasoning">
              <t-icon name="lightbulb" /> <span>深度思考 (R1)</span>
            </div>
            <div class="tool-btn upload-btn" @click="triggerUpload">
              <t-icon name="link" /> <span>上传附件</span>
            </div>
            <input type="file" ref="fileInput" style="display: none" @change="handleFileUpload" />
          </div>

          <div class="input-row">
            <t-textarea
              v-model="txt"
              :placeholder="isReasoning ? '深度思考模式...' : '发送消息...'"
              :autosize="{ minRows: 1, maxRows: 6 }"
              @keydown.enter.prevent="handleEnter"
              class="main-textarea"
            />
            <t-button shape="square" theme="primary" class="send-btn" @click="handleSend" :loading="busy">
               <template #icon><t-icon name="arrow-up" /></template>
            </t-button>
          </div>
        </div>
        <div class="disclaimer">DeepSeek 生成内容仅供参考，请核实重要信息。</div>
      </div>
    </template>

    <div v-else class="empty-state">
      <div class="empty-content">
        <div class="logo-box"><t-icon name="chat" size="40px" style="color: #4d71ff" /></div>
        <h1>DeepSeek AI</h1>
        <p>请点击左上角的「新建对话」开始</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, watch } from 'vue';
import { useUserStore } from '../stores/user';
import { api } from '../api';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import { MessagePlugin } from 'tdesign-vue-next';
import texmath from 'markdown-it-texmath';
import katex from 'katex';
import 'katex/dist/katex.min.css';

const props = defineProps(['sessionId']);
const emit = defineEmits(['refresh-list']);
const store = useUserStore();

const list = ref([]);
const txt = ref('');
const busy = ref(false);
const box = ref(null);
const isReasoning = ref(false);
const fileInput = ref(null);
const uploadedFile = ref(null);

let seq = 0;
const nextId = () => 'm' + (++seq) + '_' + Date.now();

// html 关闭以规避 XSS（模型返回的原始 HTML 不执行），其余渲染能力不受影响
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(str, { language: lang }).value; } catch (e) { /* ignore */ }
    }
    return '';
  },
});

// 数学公式：支持 $...$ / $$...$$ 与 \[...\] / \(...\)
md.use(texmath, { engine: katex, delimiters: 'dollars',
  katexOptions: { macros: { '\\boxed': '\\fcolorbox{black}{white}{#1}' } } });
md.use(texmath, { engine: katex, delimiters: 'brackets' });

// 给代码块加上语言标签 + 一键复制按钮
const defaultFence = md.renderer.rules.fence;
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const info = (tokens[idx].info || '').trim();
  const lang = info.split(/\s+/)[0] || 'text';
  const rendered = defaultFence(tokens, idx, options, env, self);
  return '<div class="code-block">'
    + '<div class="code-head"><span class="code-lang">' + md.utils.escapeHtml(lang) + '</span>'
    + '<button type="button" class="code-copy-btn">复制</button></div>'
    + rendered + '</div>';
};

// 性能关键：Markdown 渲染结果缓存。
// 否则每次数据块到达都会让整页消息重新渲染一遍（含 KaTeX 公式、代码高亮），
// 主线程被占满 => 输入框卡顿、按键延迟才蹦出来。
const mdCache = new Map();
const renderMd = (text) => {
  if (!text) return '';
  let html = mdCache.get(text);
  if (html === undefined) {
    html = md.render(text);
    if (mdCache.size > 300) mdCache.clear();  // 控制内存
    mdCache.set(text, html);
  }
  return html;
};

// 只在用户本来就贴着底部时才自动滚动，避免打断向上翻阅
const scroll = (force = false) => nextTick(() => {
  const el = box.value;
  if (!el) return;
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  if (force || nearBottom) el.scrollTop = el.scrollHeight;
});

const onChatClick = async (e) => {
  const btn = e.target.closest ? e.target.closest('.code-copy-btn') : null;
  if (!btn) return;
  const block = btn.closest('.code-block');
  const pre = block ? block.querySelector('pre') : null;
  if (!pre) return;
  try {
    await navigator.clipboard.writeText(pre.innerText);
    btn.textContent = '已复制';
    setTimeout(() => { btn.textContent = '复制'; }, 1500);
  } catch (err) {
    MessagePlugin.warning('复制失败，请手动选择文本');
  }
};

watch(() => props.sessionId, async (newId) => {
  uploadedFile.value = null;
  if (newId) await loadHistory(newId);
  else list.value = [];
});

const loadHistory = async (id) => {
  try {
    const msgs = await api.listMessages(store.token, id);
    list.value = (msgs || []).map((m) => ({
      id: 'srv_' + m.id,
      role: m.role,
      content: m.content || '',
      reasoning: '',
      loading: false,
      error: '',
    }));
    scroll(true);
  } catch (e) {
    MessagePlugin.error('加载历史消息失败：' + e.message);
  }
};

const toggleReasoning = () => { isReasoning.value = !isReasoning.value; };
const triggerUpload = () => fileInput.value.click();
const clearFile = () => { uploadedFile.value = null; };

const handleFileUpload = async (e) => {
  const file = e.target.files[0];
  e.target.value = '';
  if (!file) return;
  try {
    const data = await api.upload(store.token, file);
    uploadedFile.value = { localPath: data.local_path, originalName: data.filename };
    MessagePlugin.success('上传成功：' + data.filename);
  } catch (err) {
    MessagePlugin.error(err.message);
  }
};

const handleEnter = (e) => { if (!e.shiftKey) handleSend(); };

const handleSend = async () => {
  if (!txt.value.trim() || busy.value || !props.sessionId) return;
  const msg = txt.value;
  txt.value = '';

  let displayMsg = msg;
  if (uploadedFile.value) displayMsg += '\n[附件: ' + uploadedFile.value.originalName + ']';

  list.value.push({ id: nextId(), role: 'user', content: displayMsg, reasoning: '', loading: false, error: '' });
  const aiMsg = reactive({ id: nextId(), role: 'assistant', content: '', reasoning: '', loading: true, error: '' });
  list.value.push(aiMsg);

  await nextTick();
  scroll(true);
  busy.value = true;

  const filePath = uploadedFile.value ? uploadedFile.value.localPath : null;
  uploadedFile.value = null;

  // ---- 流式节流：把高频数据块合并成约 8 次/秒的更新 ----
  let pendingR = '';
  let pendingC = '';
  let timer = null;
  const flush = () => {
    if (timer) { clearTimeout(timer); timer = null; }
    if (pendingR) { aiMsg.reasoning += pendingR; pendingR = ''; }
    if (pendingC) { aiMsg.content += pendingC; pendingC = ''; }
    aiMsg.loading = false;
    scroll();
  };
  const schedule = () => {
    if (timer) return;
    timer = setTimeout(flush, 120);
  };

  try {
    const res = await fetch(api.chatUrl(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Auth-Token': 'Bearer ' + store.token },
      body: JSON.stringify({
        message: msg,
        session_id: props.sessionId,
        is_reasoning: isReasoning.value,
        file_path: filePath,
      }),
    });

    if (!res.ok) {
      let detail = '请求失败 (' + res.status + ')';
      try { const d = await res.json(); detail = d.detail || detail; } catch (e) { /* ignore */ }
      throw new Error(detail);
    }

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += dec.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const json = JSON.parse(line);
          if (json.type === 'r') pendingR += json.text;
          else if (json.type === 'c') pendingC += json.text;
          schedule();
        } catch (e) { /* 半包 JSON，等下一块 */ }
      }
    }
  } catch (e) {
    aiMsg.error = e.message;
  } finally {
    flush();
    busy.value = false;
    aiMsg.loading = false;
    scroll();
    emit('refresh-list'); // 让侧边栏刷新（首条消息会自动命名会话）
  }
};
</script>

<style scoped>
.fixed-width-container { width: 1000px; min-width: 1000px; height: 100%; background: #fff; display: flex; flex-direction: column; border-left: 1px solid #f0f0f0; border-right: 1px solid #f0f0f0; }

.chat-history { flex: 1; overflow-y: auto; padding: 20px 0; width: 100%; position: relative; }
.chat-start-tip-container { height: 100%; display: flex; align-items: center; justify-content: center; }
.chat-start-tip-content { display: flex; align-items: center; gap: 8px; padding: 10px 20px; background: #f8f9fb; border-radius: 20px; color: #888; font-size: 14px; }
.msg-row { display: flex; gap: 16px; margin-bottom: 30px; width: 90%; max-width: 900px; margin-left: auto; margin-right: auto; padding: 0 10px; }
.msg-row.user { flex-direction: row-reverse; }
.bubble { font-size: 16px; line-height: 1.7; color: #333; padding: 0 5px; flex: 1; overflow-wrap: break-word; min-width: 0; }
.msg-row.user .bubble { background: #f4f4f4; padding: 12px 16px; border-radius: 12px; flex: initial; max-width: 80%; }
:deep(.markdown-body img) { max-width: 300px; border-radius: 8px; margin: 10px 0; display: block; }
:deep(.markdown-body p:first-child) { margin-top: 0; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
.empty-state { flex: 1; display: flex; align-items: center; justify-content: center; background: #fff; height: 100%; width: 100%; }
.logo-box { width: 60px; height: 60px; background: #eef2ff; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }
.empty-content { text-align: center; }
.empty-content h1 { font-size: 36px; margin-bottom: 10px; }
.footer-input-area { padding: 20px; background: #fff; width: 100%; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; }
.input-shadow-box { width: 95%; max-width: 1200px; background: #f4f4f4; border-radius: 16px; padding: 10px 15px; display: flex; flex-direction: column; gap: 5px; box-sizing: border-box; }
.input-shadow-box:focus-within { background: #fff; border: 1px solid #d1d1d1; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
.toolbar { display: flex; gap: 15px; padding-left: 5px; margin-bottom: 5px; }
.tool-btn { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #666; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: all 0.2s; user-select: none; }
.tool-btn:hover { background: #e3e3e3; color: #333; }
.tool-btn.active { color: #4d71ff; background: #eef2ff; font-weight: 500; }
.input-row { display: flex; align-items: flex-end; gap: 10px; width: 100%; }
.main-textarea { background: transparent; flex: 1; }
:deep(.t-textarea__inner) { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; font-size: 16px; }
.file-preview { display: flex; align-items: center; gap: 10px; background: #eef2ff; color: #4d71ff; padding: 8px 12px; border-radius: 8px; width: fit-content; margin-bottom: 5px; font-size: 13px; }
.file-preview .close-btn { cursor: pointer; }
.reasoning-box { background: #f5f5f5; border-left: 3px solid #d9d9d9; padding: 10px 15px; margin-bottom: 15px; border-radius: 4px; font-size: 14px; color: #666; }
.reasoning-title { font-weight: bold; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; color: #888; font-size: 12px; text-transform: uppercase; }
.disclaimer { text-align: center; font-size: 12px; color: #aaa; margin-top: 10px; width: 100%; }
.error-tip { margin-top: 8px; padding: 8px 12px; background: #fff1f0; border: 1px solid #ffccc7; border-radius: 8px; color: #cf1322; font-size: 13px; display: flex; align-items: center; gap: 6px; }

/* 代码块容器 + 复制按钮 */
:deep(.code-block) { position: relative; margin: 10px 0; border-radius: 8px; overflow: hidden; background: #282c34; }
:deep(.code-head) { display: flex; justify-content: space-between; align-items: center; padding: 6px 12px; background: #21252b; color: #abb2bf; font-size: 12px; }
:deep(.code-copy-btn) { background: transparent; border: 1px solid #4b5263; color: #abb2bf; border-radius: 4px; cursor: pointer; font-size: 12px; padding: 2px 8px; }
:deep(.code-copy-btn:hover) { color: #fff; border-color: #61afef; }
:deep(.code-block pre) { margin: 0; padding: 12px 14px; overflow-x: auto; }
:deep(.code-block code) { background: transparent; color: #abb2bf; }
</style>
