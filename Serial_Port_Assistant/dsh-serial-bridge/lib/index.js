/**
 * serial-bridge — DSH 串口桥插件。
 *
 * 接收串口助手推送的接收数据，把数据注入当前 Agent 会话：
 *   - chat 模式：每一条数据都 followup（唤醒 Agent 回一条，像聊天）
 *   - monitor 模式：数据进缓冲，按间隔/大小合并成一条监控消息再 followup
 *   - off：忽略
 *
 * HTTP 端点（注册在 DSH web server 上，同源 /plugins/serial-bridge/*）：
 *   POST /plugins/serial-bridge/incoming  { text, hex?, ts? }   推送数据
 *   POST /plugins/serial-bridge/mode      { mode, monitorMs? }  切换模式
 *   POST /plugins/serial-bridge/status    {}                    查询状态
 */
import { createUserMessage } from '@deepseek-ai/dsh-llm';

export const name = 'serial-bridge';

const ROUTE_PREFIX = '/plugins/serial-bridge';
const MAX_BODY_BYTES = 1024 * 1024;

export function apply(ctx) {
  // 只注入 webServer；agents 服务在运行时懒取（避免注入依赖导致加载失败）
  ctx.inject(['webServer'], (scope) => {
    mount(ctx, scope).catch((error) => {
      scope.logger.warn(`serial-bridge: setup failed: ${error?.message ?? error}`);
    });
  });
}

async function mount(ctx, scope) {
  const state = {
    mode: 'chat',
    monitorMs: 5000,
    monitorMaxChars: 2048,
    buffer: [],
    bufferChars: 0,
  };

  function agentsRegistry() {
    try {
      return ctx.get('agents') ?? scope.get('agents') ?? undefined;
    } catch {
      return undefined;
    }
  }

  // ---- 找当前（最近创建）的 Agent 会话 ----
  function latestAgent() {
    try {
      const registry = agentsRegistry();
      if (registry && typeof registry.list === 'function') {
        const list = registry.list();
        if (list.length > 0) return list[list.length - 1];
      }
      // 兜底：store 里是 entry（含 .agent 字段）
      const store = registry?.store;
      if (store && typeof store.entries === 'function') {
        let last;
        for (const [, entry] of store.entries()) last = entry?.agent ?? entry;
        return last;
      }
    } catch { /* ignore */ }
    return undefined;
  }

  // ---- 注入一条 user 消息并唤醒 Agent ----
  function pushToAgent(text) {
    const agent = latestAgent();
    if (!agent || typeof agent.followup !== 'function') {
      return {
        ok: false,
        error: `no followup (agent=${typeof agent}, followup=${typeof agent?.followup}, hasList=${typeof agentsRegistry()?.list})`,
      };
    }
    try {
      const message = createUserMessage({
        content: [{ type: 'text', text }],
        source: { kind: 'plugin', plugin: 'serial-bridge' },
      });
      agent.followup(message);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: String(error?.message ?? error) };
    }
  }

  function flushMonitor() {
    if (state.buffer.length === 0) return;
    const text = `[串口监控] ${state.buffer.join('')}`;
    state.buffer = [];
    state.bufferChars = 0;
    return pushToAgent(text);
  }

  function handleIncoming(body) {
    const text = typeof body?.text === 'string' ? body.text : '';
    if (!text) return { ok: false, error: 'empty text' };
    const mode = ['off', 'chat', 'monitor'].includes(body?.mode) ? body.mode : state.mode;
    if (mode === 'off') return { ok: true, note: 'ignored: mode=off' };
    if (mode === 'chat') {
      return pushToAgent(`[串口] ${text}`);
    }
    if (mode === 'monitor') {
      state.buffer.push(text);
      state.bufferChars += text.length;
      if (state.bufferChars >= state.monitorMaxChars) flushMonitor();
      return { ok: true, bufferedChars: state.bufferChars };
    }
    return { ok: false, error: `unknown mode ${mode}` };
  }

  function handleMode(body) {
    const mode = String(body?.mode ?? '').toLowerCase();
    if (!['off', 'chat', 'monitor'].includes(mode)) {
      return { ok: false, error: `mode must be off|chat|monitor, got "${mode}"` };
    }
    state.mode = mode;
    const ms = Number(body?.monitorMs);
    if (Number.isFinite(ms) && ms >= 500) state.monitorMs = Math.round(ms);
    if (mode !== 'monitor') flushMonitor();
    return { ok: true, mode: state.mode, monitorMs: state.monitorMs };
  }

  // ---- HTTP ----
  function readJson(req) {
    return new Promise((resolve, reject) => {
      let data = '';
      let size = 0;
      req.setEncoding('utf8');
      req.on('data', (chunk) => {
        size += chunk.length;
        if (size > MAX_BODY_BYTES) {
          reject(new Error('body too large'));
          req.destroy();
          return;
        }
        data += chunk;
      });
      req.on('end', () => {
        if (!data) return resolve(undefined);
        try {
          resolve(JSON.parse(data));
        } catch {
          reject(new Error('invalid JSON'));
        }
      });
      req.on('error', reject);
    });
  }

  function send(res, status, payload) {
    res.writeHead(status, {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    });
    res.end(JSON.stringify(payload));
  }

  async function handle(req, res) {
    let pathname;
    try {
      pathname = new URL(req.url ?? '/', 'http://x').pathname;
    } catch {
      return send(res, 400, { ok: false, error: 'bad request' });
    }
    if (req.method !== 'POST') {
      return send(res, 405, { ok: false, error: 'method not allowed' });
    }
    const mediaType = String(req.headers['content-type'] ?? '')
      .split(';', 1)[0].trim().toLowerCase();
    if (mediaType !== 'application/json') {
      return send(res, 415, { ok: false, error: 'content-type must be application/json' });
    }
    let body;
    try {
      body = await readJson(req);
    } catch (error) {
      return send(res, 400, { ok: false, error: error?.message ?? 'bad body' });
    }
    const sub = pathname === ROUTE_PREFIX ? '' : pathname.slice(ROUTE_PREFIX.length);
    let out;
    try {
      if (sub === '/incoming') out = handleIncoming(body ?? {});
      else if (sub === '/mode') out = handleMode(body ?? {});
      else if (sub === '/status') {
        const reg = agentsRegistry();
        const list = (typeof reg?.list === 'function') ? reg.list() : [];
        out = {
          ok: true,
          mode: state.mode,
          monitorMs: state.monitorMs,
          bufferedChars: state.bufferChars,
          hasAgentRegistry: !!reg,
          agentCount: list.length,
          hasAgent: !!latestAgent(),
        };
      } else {
        return send(res, 404, { ok: false, error: 'not found' });
      }
    } catch (error) {
      scope.logger.warn(`serial-bridge: ${sub} failed: ${error?.message ?? error}`);
      out = { ok: false, error: String(error?.message ?? error) };
    }
    send(res, 200, out);
  }

  const dispose = scope.webServer.register({
    kind: 'prefix',
    path: ROUTE_PREFIX,
    handler: handle,
  });
  // effect 的 setup 只返回 disposer，卸载时才调用（不能立即调用！）
  scope.effect(() => dispose, 'serial-bridge: routes');

  const timer = setInterval(() => {
    try {
      flushMonitor();
    } catch { /* timer errors are non-fatal */ }
  }, Math.max(500, state.monitorMs));
  scope.effect(() => () => clearInterval(timer), 'serial-bridge: monitor-timer');

  scope.logger.info('serial-bridge: ready');
}
