import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Layout, Input, Button, Typography, Spin, Collapse, Tag, message, Modal, Upload,
  Drawer, Radio, Slider, Table, Descriptions, Divider, Space,
} from 'antd';
import {
  SendOutlined, RobotOutlined, UserOutlined, LoadingOutlined,
  UploadOutlined, InboxOutlined, FileTextOutlined,
  SettingOutlined, PlusOutlined, DeleteOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;
const { Text, Paragraph } = Typography;

const API_BASE = '/';
const CHUNK_OPTIONS = [200, 400, 600, 800];
const THRESHOLD_MIN = 0.1, THRESHOLD_MAX = 0.9, THRESHOLD_STEP = 0.05;

// ── 高亮引用标注 ──────────────────────────────────────

function highlightCitations(text) {
  if (!text) return text;
  const re = /【([^】]+)】/g;
  const parts = [];
  let last = 0;
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(
      <Tag key={m.index} color="gold" style={{ fontWeight: 700, fontSize: 13 }}>
        {m[0]}
      </Tag>
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length > 0 ? parts : text;
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const chatEnd = useRef(null);

  // ── 配置 & 调优面板 ────────────────────────────────

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [configUpdating, setConfigUpdating] = useState(false);
  const [config, setConfig] = useState({ chunk_size: 400, similarity_threshold: 0.35, top_k: 3, total_chunks: 0, indexed_docs: 0 });
  const [experiments, setExperiments] = useState([]);
  const [newNote, setNewNote] = useState('');

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}config`);
      if (res.ok) setConfig(await res.json());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const updateConfig = async (key, value) => {
    setConfigUpdating(true);
    try {
      const body = key === 'chunk_size'
        ? { chunk_size: value }
        : { similarity_threshold: value };
      const res = await fetch(`${API_BASE}config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        message.success(data.message || '参数已更新');
        fetchConfig();
        fetchDocuments();
      } else {
        message.error(data.detail || '更新失败');
      }
    } catch {
      message.error('网络错误');
    } finally {
      setConfigUpdating(false);
    }
  };

  const addExperiment = () => {
    setExperiments(prev => [{
      key: Date.now(),
      chunk_size: config.chunk_size,
      similarity_threshold: config.similarity_threshold,
      question: input || '(未输入)',
      rating: '',
      note: newNote,
    }, ...prev]);
    setNewNote('');
  };

  const delExperiment = key => setExperiments(prev => prev.filter(e => e.key !== key));

  const expColumns = [
    { title: 'chunk_size', dataIndex: 'chunk_size', width: 90 },
    { title: '阈值', dataIndex: 'similarity_threshold', width: 70,
      render: v => v?.toFixed(2) },
    { title: '测试问题', dataIndex: 'question', ellipsis: true },
    { title: '评分(1-5)', dataIndex: 'rating', width: 90,
      render: (v, r) => (
        <Radio.Group size="small" value={v} onChange={e => {
          setExperiments(prev => prev.map(x => x.key === r.key ? { ...x, rating: e.target.value } : x));
        }}>
          {[1,2,3,4,5].map(n => <Radio.Button key={n} value={String(n)}>{n}</Radio.Button>)}
        </Radio.Group>
      ),
    },
    { title: '备注', dataIndex: 'note', ellipsis: true, width: 120 },
    { title: '', width: 40,
      render: (_, r) => <Button size="small" type="text" danger icon={<DeleteOutlined />}
                                onClick={() => delExperiment(r.key)} />,
    },
  ];

  // ── 文档加载 ────────────────────────────────────────

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}documents`);
      if (res.ok) setDocuments(await res.json());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // ── 发送消息（SSE 流式） ──────────────────────────

  const sendMessage = async () => {
    const question = input.trim();
    if (!question) return message.warning('请输入研究问题');
    setInput('');
    setLoading(true);

    const userMsg = { role: 'user', content: question };
    const aiMsg = { role: 'assistant', content: '', sources: [], streaming: true };
    setMessages(prev => [...prev, userMsg, aiMsg]);

    try {
      const res = await fetch(`${API_BASE}query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `请求失败 (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '', fullAnswer = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) {
              fullAnswer += data.chunk;
              setMessages(prev => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === 'assistant')
                  next[next.length - 1] = { ...last, content: fullAnswer, streaming: true };
                return next;
              });
            }
            if (data.done) {
              const srcRes = await fetch(`${API_BASE}query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
              });
              const srcData = srcRes.ok ? await srcRes.json() : { sources: [] };
              setMessages(prev => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === 'assistant')
                  next[next.length - 1] = { ...last, content: fullAnswer, sources: srcData.sources || [], streaming: false };
                return next;
              });
            }
            if (data.error) message.error(data.error);
          } catch { /* skip */ }
        }
      }
    } catch (err) {
      message.error(err.message || '网络错误，请检查后端服务');
      setMessages(prev => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === 'assistant')
          next[next.length - 1] = { ...last, streaming: false, content: last.content || '请求失败' };
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  // ── 上传研报 ──────────────────────────────────────

  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);

  const handleUpload = async () => {
    if (!uploadFile) return message.warning('请先选择 PDF 文件');
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', uploadFile);
      const res = await fetch(`${API_BASE}upload`, { method: 'POST', body: form });
      const data = await res.json();
      if (res.ok) {
        message.success(`${data.filename} — ${data.chunks} 个分块，已加入知识库`);
        setUploadOpen(false);
        setUploadFile(null);
        fetchDocuments();
      } else {
        message.error(data.detail || '上传失败');
      }
    } catch {
      message.error('网络错误，请检查后端服务');
    } finally {
      setUploading(false);
    }
  };

  // ── 渲染 ──────────────────────────────────────────

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'linear-gradient(135deg, #1a3a5c 0%, #2d6aa0 100%)',
        padding: '0 24px',
      }}>
        <span style={{ fontSize: 20 }}>📊</span>
        <Text strong style={{ color: '#fff', fontSize: 18, flex: 1 }}>
          券商研报智能问答系统
        </Text>
        <Button type="text" icon={<SettingOutlined />} onClick={() => setDrawerOpen(true)}
                style={{ color: '#fff', fontSize: 16 }}>⚙️ 参数调优</Button>
        <Tag color="gold" icon={<RobotOutlined />} style={{ fontSize: 14, padding: '2px 12px' }}>
          🎩 某券商首席分析师助理
        </Tag>
      </Header>

      <Layout>
        <Sider width={280} style={{ background: '#fafafa', padding: 16, overflow: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <Text strong style={{ fontSize: 15 }}>📄 研报知识库</Text>
            <Button type="primary" size="small" icon={<UploadOutlined />}
                    onClick={() => setUploadOpen(true)}>上传</Button>
          </div>
          <div>
            {documents.length === 0 && (
              <Text type="secondary" style={{ fontSize: 13 }}>暂无研报，点击上传 PDF</Text>
            )}
            {documents.map(d => (
              <div key={d.id} style={{
                padding: '10px 12px', marginBottom: 8, background: '#fff',
                borderRadius: 6, border: '1px solid #e8e8e8',
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <FileTextOutlined style={{ color: '#1677ff', marginTop: 2 }} />
                  <div style={{ flex: 1 }}>
                    <Text strong style={{ fontSize: 13 }}>{d.report_name}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      📑 {d.chunks} 分块 · {d.uploaded_at}
                    </Text>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <Modal title="📄 上传研报" open={uploadOpen}
            onCancel={() => { setUploadOpen(false); setUploadFile(null); }}
            footer={[
              <Button key="cancel" onClick={() => { setUploadOpen(false); setUploadFile(null); }}>取消</Button>,
              <Button key="upload" type="primary" loading={uploading} onClick={handleUpload}
                      icon={<UploadOutlined />}>上传到知识库</Button>,
            ]}
          >
            <Upload.Dragger accept=".pdf" maxCount={1}
              beforeUpload={file => { setUploadFile(file); return false; }}
              onRemove={() => setUploadFile(null)}
              fileList={uploadFile ? [uploadFile] : []}
              style={{ padding: '24px 0' }}
            >
              <p className="ant-upload-drag-icon" style={{ fontSize: 40 }}><InboxOutlined /></p>
              <p className="ant-upload-text" style={{ fontSize: 15 }}>点击或拖拽 PDF 文件到此区域</p>
              <p className="ant-upload-hint" style={{ fontSize: 13 }}>仅支持 .pdf 格式，单份研报上传</p>
            </Upload.Dragger>
            {uploading && <div style={{ marginTop: 16 }}><Spin tip="正在解析研报并建立索引..." /></div>}
          </Modal>
        </Sider>

        <Content style={{ display: 'flex', flexDirection: 'column', background: '#f0f2f5' }}>
          <div style={{ flex: 1, overflow: 'auto', padding: '24px 32px' }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', marginTop: 120 }}>
                <RobotOutlined style={{ fontSize: 56, color: '#bbb' }} />
                <Paragraph type="secondary" style={{ marginTop: 16, fontSize: 16 }}>
                  🎩 我是某券商首席分析师助理，请问您想了解什么？
                </Paragraph>
                <Paragraph type="secondary" style={{ fontSize: 13 }}>
                  示例：宁德时代2025年产能规划是多少？
                </Paragraph>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 20 }}>
                <div style={{ maxWidth: '75%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4,
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                    {msg.role === 'assistant' && <Tag color="blue">🎩 分析师助理</Tag>}
                    {msg.role === 'user' && <Tag><UserOutlined /> 您</Tag>}
                  </div>

                  <div style={{ padding: '14px 18px', borderRadius: 12,
                    background: msg.role === 'user' ? '#1677ff' : '#fff',
                    color: msg.role === 'user' ? '#fff' : '#333',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                    lineHeight: 1.8, fontSize: 15, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  }}>
                    {msg.role === 'assistant' ? highlightCitations(msg.content) : msg.content}
                    {msg.streaming && <Spin indicator={<LoadingOutlined style={{ fontSize: 14 }} spin />}
                                            style={{ marginLeft: 4 }} />}
                  </div>

                  {msg.role === 'assistant' && msg.sources?.length > 0 && (
                    <Collapse size="small" style={{ marginTop: 8, background: '#fff' }}
                      items={[{ key: 'sources',
                        label: <Text style={{ fontSize: 13 }}>📎 引用来源 ({msg.sources.length})</Text>,
                        children: msg.sources.map((s, j) => (
                          <div key={j} style={{ padding: '8px 0',
                            borderBottom: j < msg.sources.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                            <Text strong style={{ fontSize: 13, color: '#1677ff' }}>
                              📄 {s.report_name} 第 {s.page_number} 页
                            </Text>
                            <Paragraph style={{ margin: '4px 0 0', fontSize: 13, color: '#666',
                              background: '#fafafa', padding: 8, borderRadius: 4 }} ellipsis={{ rows: 3 }}>
                              📝 {s.snippet}...
                            </Paragraph>
                          </div>
                        )),
                      }]}
                    />
                  )}
                </div>
              </div>
            ))}

            {loading && <div style={{ textAlign: 'center', marginBottom: 16 }}><Spin tip="正在查阅研报中..." /></div>}
            <div ref={chatEnd} />
          </div>

          <div style={{ padding: '16px 32px', background: '#fff', borderTop: '1px solid #e8e8e8' }}>
            <div style={{ display: 'flex', gap: 12, maxWidth: 900, margin: '0 auto' }}>
              <Input.TextArea value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={onKeyDown} placeholder="输入研究问题，按 Enter 发送，Shift+Enter 换行..."
                autoSize={{ minRows: 1, maxRows: 4 }} disabled={loading} style={{ fontSize: 15 }} />
              <Button type="primary" icon={<SendOutlined />} onClick={sendMessage}
                      loading={loading} size="large">发送</Button>
            </div>
          </div>
        </Content>
      </Layout>

      {/* ── ⚙️ 参数调优抽屉 ── */}
      <Drawer title="⚙️ RAG 参数调优实验" open={drawerOpen} onClose={() => setDrawerOpen(false)}
              width={480} extra={
        <Button onClick={() => setDrawerOpen(false)}>关闭</Button>
      }>
        {/* 当前参数 */}
        <Descriptions title="📊 当前配置" column={2} size="small" bordered
          style={{ marginBottom: 16 }}>
          <Descriptions.Item label="chunk_size">{config.chunk_size}</Descriptions.Item>
          <Descriptions.Item label="相似度阈值">{config.similarity_threshold?.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="top_k">{config.top_k}</Descriptions.Item>
          <Descriptions.Item label="索引分块数">{config.total_chunks || documents.reduce((s, d) => s + (d.chunks || 0), 0)}</Descriptions.Item>
        </Descriptions>

        <Divider />

        {/* chunk_size */}
        <Text strong>🔤 chunk_size 分块大小</Text>
        <Paragraph type="secondary" style={{ fontSize: 13, marginTop: 4 }}>
          分块越大，上下文越完整，但小模型可能消化不了
        </Paragraph>
        <Radio.Group value={config.chunk_size}
          onChange={e => updateConfig('chunk_size', e.target.value)}
          disabled={configUpdating}
          style={{ marginBottom: 24 }}
        >
          {CHUNK_OPTIONS.map(v => (
            <Radio.Button key={v} value={v} style={{ marginRight: 8 }}>{v}</Radio.Button>
          ))}
        </Radio.Group>
        {configUpdating && <Spin tip="正在重建索引..." style={{ marginLeft: 12 }} />}

        <Divider />

        {/* similarity_threshold */}
        <Text strong>🎯 similarity_threshold 相似度阈值</Text>
        <Paragraph type="secondary" style={{ fontSize: 13, marginTop: 4 }}>
          阈值越高，结果越精确但可能找不到；阈值越低，结果越多但可能不相关
        </Paragraph>
        <div style={{ marginBottom: 24 }}>
          <Slider min={THRESHOLD_MIN} max={THRESHOLD_MAX} step={THRESHOLD_STEP}
            value={config.similarity_threshold} disabled={configUpdating}
            onChange={v => setConfig(prev => ({ ...prev, similarity_threshold: v }))}
            onAfterChange={v => updateConfig('similarity_threshold', v)}
            marks={{ 0.1: '0.1', 0.3: '0.3', 0.5: '0.5', 0.7: '0.7', 0.9: '0.9' }}
          />
          <Text type="secondary" style={{ float: 'right' }}>当前: {config.similarity_threshold?.toFixed(2)}</Text>
        </div>

        <Divider />

        {/* 实验记录 */}
        <Text strong style={{ fontSize: 15 }}>🧪 实验对比记录</Text>
        <Paragraph type="secondary" style={{ fontSize: 13, marginTop: 4 }}>
          记录每次调参后的测试结果，用于 Part 4 实验分析
        </Paragraph>

        <Space direction="vertical" style={{ width: '100%', marginBottom: 12 }}>
          <Input.TextArea rows={2} value={newNote} onChange={e => setNewNote(e.target.value)}
            placeholder="备注（如：回答质量明显下降）" style={{ fontSize: 13 }} />
          <Button icon={<PlusOutlined />} onClick={addExperiment} block>
            记录当前实验 ({config.chunk_size} / {config.similarity_threshold?.toFixed(2)})
          </Button>
        </Space>

        <Table columns={expColumns} dataSource={experiments} size="small"
          pagination={{ pageSize: 10 }} scroll={{ x: 600 }}
          locale={{ emptyText: '暂无记录，调参后点击上方按钮添加' }}
        />
      </Drawer>
    </Layout>
  );
}
