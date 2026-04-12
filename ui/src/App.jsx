import { useState, useEffect, useRef } from 'react'

const SAMPLE = `diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,4 +1,8 @@
 import os
+import subprocess

 def run_command(user_input):
-    return os.system(user_input)
+    password = "hardcoded_secret_123"
+    query = "SELECT * FROM users WHERE id=" + user_input
+    result = subprocess.run(user_input, shell=True)
+    return result`

const TYPING_MSGS = [
  'Parsing diff...',
  'Loading belief system...',
  'Cross-referencing rules...',
  'Generating review...',
]

const G = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#09090c}
  ::-webkit-scrollbar{width:4px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:#2a2a3a;border-radius:4px}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  @keyframes slideup{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
  @keyframes glow{0%,100%{box-shadow:0 0 0 0 rgba(249,115,22,.15)}50%{box-shadow:0 0 0 8px rgba(249,115,22,0)}}
  .msg{animation:fadein .3s ease forwards}
  .review-anim{animation:slideup .35s ease forwards}
  .spin{animation:spin .7s linear infinite}
  textarea:focus,input:focus{border-color:rgba(249,115,22,.5)!important;outline:none}
`

function sevStyle(s) {
  if (s === 'high') return { bg: '#1e0a0a', border: 'rgba(226,75,74,.35)', bb: '#3f1515', bt: '#f87171', lbl: 'HIGH' }
  if (s === 'medium') return { bg: '#1a1400', border: 'rgba(245,158,11,.3)', bb: '#3a2800', bt: '#fbbf24', lbl: 'MED' }
  return { bg: '#080e1e', border: 'rgba(59,130,246,.3)', bb: '#0a1830', bt: '#60a5fa', lbl: 'LOW' }
}

function IssueCard({ issue }) {
  const [open, setOpen] = useState(false)
  const st = sevStyle(issue.severity)
  return (
    <div style={{ background: st.bg, border: `1px solid ${st.border}`, borderRadius: 10, marginBottom: 8, overflow: 'hidden' }}>
      <div onClick={() => setOpen(v => !v)} style={{ padding: '12px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ background: st.bb, color: st.bt, fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace', flexShrink: 0 }}>{st.lbl}</span>
        <span style={{ background: '#1a1a28', color: '#555', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace', flexShrink: 0 }}>{issue.type}</span>
        {issue.file && <span style={{ fontSize: 11, color: '#555', fontFamily: 'monospace', flexShrink: 0 }}>{issue.file}</span>}
        <span style={{ fontSize: 12, color: '#ccc', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{issue.message}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" style={{ flexShrink: 0, transition: 'transform .2s', transform: open ? 'rotate(180deg)' : 'none' }}>
          <path d="M2 4l4 4 4-4" stroke="#444" strokeWidth="1.5" fill="none" />
        </svg>
      </div>
      {open && (
        <div style={{ borderTop: `1px solid ${st.border}`, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: '#2a2a3a', marginBottom: 4, fontFamily: 'monospace' }}>suggested fix</div>
          <div style={{ background: '#0f0f14', borderRadius: 6, padding: '10px 12px', fontSize: 11, color: '#7a9a7a', fontFamily: 'monospace', lineHeight: 1.6, marginBottom: 8 }}>{issue.suggestion}</div>
          {issue.reference && (
            <div style={{ fontSize: 11, color: '#f97316', opacity: 0.6, fontFamily: 'monospace', marginBottom: 10 }}>⟶ {issue.reference}</div>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => navigator.clipboard?.writeText(issue.suggestion)} style={{ background: 'transparent', color: '#4a4a5e', border: '1px solid #1f1f2e', borderRadius: 6, padding: '5px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit' }}>Copy fix</button>
            <button style={{ background: 'transparent', color: '#2a5a2a', border: '1px solid #1a3a1a', borderRadius: 6, padding: '5px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit' }}>Mark resolved</button>
          </div>
        </div>
      )}
    </div>
  )
}

function ReviewOutput({ result, onPost, posted }) {
  const issues = result?.issues ?? []
  const high = issues.filter(i => i.severity === 'high').length
  const med = issues.filter(i => i.severity === 'medium').length
  return (
    <div className="review-anim">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#e24b4a' }} />
        <span style={{ fontSize: 13, fontWeight: 500, color: '#e4e4f0' }}>Review complete — request changes</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginBottom: 12 }}>
        {[[issues.length, '#e4e4f0', 'total'], [high, '#f87171', 'high'], [med, '#fbbf24', 'medium']].map(([n, c, l]) => (
          <div key={l} style={{ background: '#14141c', borderRadius: 10, padding: 12, textAlign: 'center', border: `1px solid ${c}22` }}>
            <div style={{ fontSize: 26, fontWeight: 600, color: c, fontFamily: 'monospace' }}>{n}</div>
            <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '.8px', marginTop: 2 }}>{l}</div>
          </div>
        ))}
      </div>
      <div style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 10, padding: '12px 14px', marginBottom: 12, fontSize: 12, color: '#888', lineHeight: 1.7 }}>{result?.summary}</div>
      <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1.2px', fontFamily: 'monospace', marginBottom: 8 }}>Issues</div>
      {issues.map((issue, i) => <IssueCard key={i} issue={issue} />)}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        {posted
          ? <div style={{ background: 'rgba(34,197,94,.1)', color: '#22c55e', border: '1px solid rgba(34,197,94,.2)', borderRadius: 8, padding: '8px 16px', fontSize: 12 }}>Posted to GitHub ✓</div>
          : <button onClick={onPost} style={{ background: 'rgba(249,115,22,.1)', color: '#f97316', border: '1px solid rgba(249,115,22,.2)', borderRadius: 8, padding: '8px 16px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>Post to GitHub</button>
        }
        <button style={{ background: 'transparent', color: '#4a4a5e', border: '1px solid #1f1f2e', borderRadius: 8, padding: '8px 14px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>Copy markdown</button>
      </div>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('review')
  const [mode, setMode] = useState('diff')
  const [diff, setDiff] = useState('')
  const [ghRepo, setGhRepo] = useState('')
  const [prNum, setPrNum] = useState('')
  const [postComment, setPostComment] = useState(false)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [typingMsg, setTypingMsg] = useState('')
  const [beliefs, setBeliefs] = useState({ rules: [], past_decisions: [] })
  const [history, setHistory] = useState([])
  const [postedSet, setPostedSet] = useState(new Set())
  const chatRef = useRef(null)

  useEffect(() => {
    fetch('/api/beliefs').then(r => r.json()).then(setBeliefs).catch(() => {})
  }, [])

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages, loading])

  const runReview = async (forceDiff) => {
    const diffText = forceDiff || diff.trim() || SAMPLE
    if (!forceDiff) setDiff(diffText)
    setLoading(true)
    setMessages(m => [...m, { type: 'user', diff: diffText }])

    let i = 0
    setTypingMsg(TYPING_MSGS[0])
    const iv = setInterval(() => { i++; if (i < TYPING_MSGS.length) setTypingMsg(TYPING_MSGS[i]) }, 700)

    try {
      const body = mode === 'diff'
        ? { repo: 'owner/repo', pr_number: 1, diff: diffText, post_comment: postComment }
        : { repo: ghRepo, pr_number: parseInt(prNum), post_comment: postComment }

      const resp = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      clearInterval(iv)
      setLoading(false)
      if (!resp.ok) throw new Error(data.detail || 'Review failed')
      setMessages(m => [...m, { type: 'review', data, idx: m.length + 1 }])
      setHistory(h => [{ repo: body.repo, pr: body.pr_number, result: data.review }, ...h])
      fetch('/api/beliefs').then(r => r.json()).then(setBeliefs).catch(() => {})
    } catch (e) {
      clearInterval(iv)
      setLoading(false)
      setMessages(m => [...m, { type: 'error', text: e.message }])
    }
  }

  const navBtn = (t) => ({
    padding: '6px 14px', borderRadius: 6, fontSize: 12, border: 'none', cursor: 'pointer',
    fontFamily: 'inherit', transition: 'all .15s',
    background: tab === t ? '#1a1a24' : 'transparent',
    color: tab === t ? '#e4e4f0' : '#4a4a5e',
  })

  const modeBtn = (m) => ({
    padding: '4px 12px', borderRadius: 6, fontSize: 11, border: 'none', cursor: 'pointer',
    fontFamily: 'monospace', transition: 'all .15s',
    background: mode === m ? '#f97316' : '#1a1a24',
    color: mode === m ? '#0c0c0f' : '#4a4a5e',
  })

  return (
    <>
      <style>{G}</style>
      <div style={{ height: '100vh', background: '#09090c', display: 'flex', flexDirection: 'column', fontFamily: "'Inter', system-ui, sans-serif", color: '#e4e4f0' }}>

        <div style={{ height: 52, borderBottom: '1px solid #1f1f2e', display: 'flex', alignItems: 'center', padding: '0 20px', flexShrink: 0, background: '#0f0f14' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 28 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#f97316' }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: '#f97316', fontFamily: 'monospace' }}>ReviewAgent</span>
          </div>
          {['review', 'history', 'rules'].map(t => (
            <button key={t} style={navBtn(t)} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
              {t === 'history' && history.length > 0 && (
                <span style={{ marginLeft: 6, background: '#1f1f2e', color: '#4a4a5e', fontSize: 10, padding: '1px 6px', borderRadius: 10 }}>{history.length}</span>
              )}
            </button>
          ))}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
            <span style={{ fontSize: 11, color: '#2a5a2a', fontFamily: 'monospace' }}>live</span>
          </div>
        </div>

        {tab === 'review' && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div ref={chatRef} style={{ flex: 1, overflowY: 'auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860, width: '100%', margin: '0 auto', alignSelf: 'center', width: '100%' }}>
              {messages.length === 0 && !loading && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, minHeight: 380 }}>
                  <div style={{ width: 56, height: 56, borderRadius: '50%', border: '1.5px solid #1f1f2e', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'glow 3s ease infinite' }}>
                    <div style={{ width: 20, height: 20, borderRadius: '50%', border: '1.5px solid #2a2a3a' }} />
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 15, color: '#4a4a5e', marginBottom: 6 }}>Drop a diff or connect a PR</div>
                    <div style={{ fontSize: 12, color: '#2a2a3a' }}>I'll review it against your team's belief system</div>
                  </div>
                  <button onClick={() => runReview(SAMPLE)} style={{ background: '#14141c', color: '#4a4a5e', border: '1px solid #1f1f2e', borderRadius: 8, padding: '8px 16px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                    Try sample diff
                  </button>
                </div>
              )}

              {messages.map((msg, idx) => {
                if (msg.type === 'user') return (
                  <div key={idx} className="msg" style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{ background: '#1a1a24', border: '1px solid #1f1f2e', borderRadius: '12px 12px 4px 12px', padding: '12px 16px', maxWidth: '75%' }}>
                      <div style={{ fontSize: 10, color: '#2a2a3a', fontFamily: 'monospace', marginBottom: 6 }}>diff pasted</div>
                      <pre style={{ fontSize: 11, color: '#666', fontFamily: 'monospace', lineHeight: 1.5, whiteSpace: 'pre-wrap', maxHeight: 80, overflow: 'hidden' }}>{msg.diff.slice(0, 220)}...</pre>
                    </div>
                  </div>
                )
                if (msg.type === 'review') return (
                  <div key={idx} className="msg">
                    <ReviewOutput
                      result={msg.data.review}
                      posted={postedSet.has(idx)}
                      onPost={() => setPostedSet(s => new Set([...s, idx]))}
                    />
                  </div>
                )
                if (msg.type === 'error') return (
                  <div key={idx} className="msg" style={{ background: '#1e0a0a', border: '1px solid rgba(226,75,74,.3)', borderRadius: 10, padding: '12px 16px', fontSize: 12, color: '#f87171', fontFamily: 'monospace' }}>
                    Error: {msg.text}
                    <button onClick={() => runReview()} style={{ marginLeft: 12, background: 'transparent', color: '#f97316', border: '1px solid rgba(249,115,22,.3)', borderRadius: 6, padding: '3px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit' }}>Retry</button>
                  </div>
                )
                return null
              })}

              {loading && (
                <div className="msg" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', background: '#14141c', border: '1px solid #1f1f2e', borderRadius: '12px 12px 12px 4px', width: 'fit-content' }}>
                  <div className="spin" style={{ width: 14, height: 14, border: '2px solid #1f1f2e', borderTop: '2px solid #f97316', borderRadius: '50%' }} />
                  <span style={{ fontSize: 12, color: '#4a4a5e', fontFamily: 'monospace' }}>{typingMsg}</span>
                </div>
              )}
            </div>

            <div style={{ padding: '12px 20px 16px', borderTop: '1px solid #1f1f2e', background: '#0f0f14', flexShrink: 0 }}>
              <div style={{ maxWidth: 860, margin: '0 auto' }}>
                <div style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 12, padding: '12px 14px' }}>
                  <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
                    {['diff', 'github'].map(m => (
                      <button key={m} style={modeBtn(m)} onClick={() => setMode(m)}>
                        {m === 'diff' ? 'paste diff' : 'github pr'}
                      </button>
                    ))}
                  </div>
                  {mode === 'diff' ? (
                    <textarea rows={3} style={{ width: '100%', background: 'transparent', border: 'none', color: '#bbb', fontSize: 12, fontFamily: 'monospace', resize: 'none', lineHeight: 1.6 }} placeholder="Paste git diff here..." value={diff} onChange={e => setDiff(e.target.value)} />
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 8 }}>
                      <input style={{ background: '#1a1a24', border: '1px solid #1f1f2e', borderRadius: 6, padding: '8px 10px', color: '#ccc', fontSize: 12, fontFamily: 'monospace', width: '100%' }} placeholder="owner/repo" value={ghRepo} onChange={e => setGhRepo(e.target.value)} />
                      <input style={{ background: '#1a1a24', border: '1px solid #1f1f2e', borderRadius: 6, padding: '8px 10px', color: '#ccc', fontSize: 12, fontFamily: 'monospace', width: '100%' }} placeholder="PR #" type="number" value={prNum} onChange={e => setPrNum(e.target.value)} />
                    </div>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, paddingTop: 10, borderTop: '1px solid #1f1f2e' }}>
                    <button onClick={() => runReview()} disabled={loading} style={{ background: '#f97316', color: '#0c0c0f', border: 'none', borderRadius: 8, padding: '8px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', opacity: loading ? 0.5 : 1 }}>
                      {loading ? 'Reviewing...' : 'Run review'}
                    </button>
                    <button onClick={() => setDiff(SAMPLE)} style={{ background: 'transparent', color: '#4a4a5e', border: '1px solid #1f1f2e', borderRadius: 8, padding: '8px 12px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>Load sample</button>
                    <label style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#2a2a3a', cursor: 'pointer' }}>
                      <input type="checkbox" checked={postComment} onChange={e => setPostComment(e.target.checked)} style={{ accentColor: '#f97316' }} /> Post to GitHub
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'rules' && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <span style={{ fontSize: 13, color: '#4a4a5e' }}>Active belief system</span>
              <button style={{ background: 'transparent', color: '#f97316', border: '1px solid rgba(249,115,22,.3)', borderRadius: 6, padding: '5px 12px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit' }}>+ Add rule</button>
            </div>
            <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'monospace', marginBottom: 8 }}>Rules ({beliefs.rules.length})</div>
            {beliefs.rules.map((r, i) => (
              <div key={i} style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 10, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#f97316', flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: '#bbb', fontFamily: 'monospace', lineHeight: 1.5, flex: 1 }}>{r}</span>
              </div>
            ))}
            <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'monospace', margin: '16px 0 8px' }}>Past decisions ({beliefs.past_decisions.length})</div>
            {beliefs.past_decisions.map((d, i) => (
              <div key={i} style={{ background: '#0f0f14', border: '1px solid #1a1a24', borderRadius: 10, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#2a2a3a', flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: '#4a4a5e', fontFamily: 'monospace', lineHeight: 1.5 }}>{d}</span>
              </div>
            ))}
          </div>
        )}

        {tab === 'history' && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
            <div style={{ fontSize: 13, color: '#4a4a5e', marginBottom: 16 }}>Past reviews this session</div>
            {history.length === 0
              ? <div style={{ fontSize: 12, color: '#2a2a3a', fontFamily: 'monospace' }}>No reviews yet.</div>
              : <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {history.map((h, i) => {
                  const high = h.result?.issues?.filter(x => x.severity === 'high').length ?? 0
                  const med = h.result?.issues?.filter(x => x.severity === 'medium').length ?? 0
                  return (
                    <div key={i} onClick={() => setTab('review')} style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 12, padding: 14, cursor: 'pointer' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#e24b4a' }} />
                        <span style={{ fontSize: 12, color: '#e4e4f0' }}>{h.repo} · PR #{h.pr}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#4a4a5e', marginBottom: 8, lineHeight: 1.5 }}>{h.result?.summary?.slice(0, 90)}...</div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {high > 0 && <span style={{ background: '#2a1010', color: '#f87171', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace' }}>{high} high</span>}
                        {med > 0 && <span style={{ background: '#2a1a00', color: '#fbbf24', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace' }}>{med} medium</span>}
                      </div>
                    </div>
                  )
                })}
              </div>
            }
          </div>
        )}
      </div>
    </>
  )
}
