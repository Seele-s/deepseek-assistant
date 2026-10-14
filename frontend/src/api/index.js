// 统一 API 层：所有后端调用集中在这里，杜绝 URL 硬编码散落在各组件里。
// 开发环境读 .env.development；生产构建时 VITE_API_BASE 为空 => 同源部署。
const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

export const apiBase = BASE;

// 注意：网关（Basic Auth）占用了 Authorization 头，
// 所以应用自身的 JWT 用自定义头 X-Auth-Token，避免互相覆盖。
function headers(token, extra = {}) {
  return token ? { ...extra, 'X-Auth-Token': 'Bearer ' + token } : extra;
}

async function request(path, { method = 'GET', token, body, form = false } = {}) {
  const opts = { method, headers: headers(token, form ? {} : (body ? { 'Content-Type': 'application/json' } : {})) };
  if (body) opts.body = form ? body : JSON.stringify(body);

  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    let detail = '请求失败 (' + res.status + ')';
    try { const data = await res.json(); detail = data.detail || detail; } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  login(username, password) {
    const body = new URLSearchParams({ username, password });
    return request('/api/token', { method: 'POST', body, form: true });
  },
  register(username, password) {
    return request('/api/register', { method: 'POST', body: { username, password } });
  },
  me(token) {
    return request('/api/me', { token });
  },
  listSessions(token) {
    return request('/api/sessions', { token });
  },
  createSession(token, title = '新对话') {
    return request('/api/sessions', { method: 'POST', token, body: { title } });
  },
  renameSession(token, id, title) {
    return request('/api/sessions/' + id, { method: 'PATCH', token, body: { title } });
  },
  deleteSession(token, id) {
    return request('/api/sessions/' + id, { method: 'DELETE', token });
  },
  listMessages(token, id) {
    return request('/api/sessions/' + id + '/messages', { token });
  },
  async upload(token, file) {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(BASE + '/api/upload', { method: 'POST', headers: headers(token), body: form });
    if (!res.ok) {
      let detail = '上传失败';
      try { const d = await res.json(); detail = d.detail || detail; } catch (e) { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  },
  chatUrl() {
    return BASE + '/api/chat';
  },
  fileUrl(name) {
    return BASE + '/api/files/' + name;
  },
};
