import { useState, useEffect, useRef } from 'react'

const TYPING_MSGS = [
  'Fetching PR diff from GitHub...',
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
  @keyframes countup{from{opacity:0}to{opacity:1}}
  .msg{animation:fadein .3s ease forwards}
  .review-anim{animation:slideup .35s ease forwards}
  .spin{animation:spin .7s linear infinite}
  textarea:focus,input:focus{border-color:rgba(249,115,22,.5)!important;outline:none}
  button:active{transform:scale(.97)}
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
        {issue.confidence && <span style={{ background: '#1a1a1a', color: '#444', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace', flexShrink: 0 }}>{issue.confidence}%</span>}
        <span style={{ fontSize: 12, color: '#ccc', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{issue.message}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" style={{ flexShrink: 0, transition: 'transform .2s', transform: open ? 'rotate(180deg)' : 'none' }}>
          <path d="M2 4l4 4 4-4" stroke="#444" strokeWidth="1.5" fill="none" />
        </svg>
      </div>
      {open && (
        <div style={{ borderTop: `1px solid ${st.border}`, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: '#2a2a3a', marginBottom: 4, fontFamily: 'monospace' }}>suggested fix</div>
          <div style={{ background: '#0f0f14', borderRadius: 6, padding: '10px 12px', fontSize: 11, color: '#7a9a7a', fontFamily: 'monospace', lineHeight: 1.6, marginBottom: 8 }}>{issue.suggestion}</div>
          {issue.reference && <div style={{ fontSize: 11, color: '#f97316', opacity: 0.6, fontFamily: 'monospace', marginBottom: 10 }}>⟶ {issue.reference}</div>}
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
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: high > 0 ? '#e24b4a' : '#22c55e' }} />
        <span style={{ fontSize: 13, fontWeight: 500, color: '#e4e4f0' }}>
          {high > 0 ? 'Review complete — request changes' : 'Review complete — looks good'}
        </span>
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
      {issues.length > 0 && <>
        <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1.2px', fontFamily: 'monospace', marginBottom: 8 }}>Issues</div>
        {issues.map((issue, i) => <IssueCard key={i} issue={issue} />)}
      </>}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        {posted
          ? <div style={{ background: 'rgba(34,197,94,.1)', color: '#22c55e', border: '1px solid rgba(34,197,94,.2)', borderRadius: 8, padding: '8px 16px', fontSize: 12 }}>Posted to GitHub ✓</div>
          : <button onClick={onPost} style={{ background: 'rgba(249,115,22,.1)', color: '#f97316', border: '1px solid rgba(249,115,22,.2)', borderRadius: 8, padding: '8px 16px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>Post to GitHub</button>
        }
        <button onClick={() => navigator.clipboard?.writeText(result?.comment || '')} style={{ background: 'transparent', color: '#4a4a5e', border: '1px solid #1f1f2e', borderRadius: 8, padding: '8px 14px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>Copy markdown</button>
      </div>
    </div>
  )
}

function MetricCard({ label, value, color, sub }) {
  return (
    <div style={{ background: '#14141c', border: `1px solid ${color}22`, borderRadius: 12, padding: '16px 20px' }}>
      <div style={{ fontSize: 11, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'monospace', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 600, color, fontFamily: 'monospace', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#3a3a4a', marginTop: 6, fontFamily: 'monospace' }}>{sub}</div>}
    </div>
  )
}

function Dashboard({ metrics }) {
  const avgConf = metrics.totalIssues > 0
    ? Math.round(metrics.totalConfidence / metrics.totalIssues)
    : 0

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
      <div style={{ fontSize: 13, color: '#4a4a5e', marginBottom: 20 }}>Session metrics</div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12, marginBottom: 20 }}>
        <MetricCard label="PRs reviewed" value={metrics.prsReviewed} color="#e4e4f0" sub="this session" />
        <MetricCard label="Issues found" value={metrics.totalIssues} color="#f87171" sub={`${metrics.highCount} high severity`} />
        <MetricCard label="Avg confidence" value={`${avgConf}%`} color="#f97316" sub="across all issues" />
        <MetricCard label="Beliefs updated" value={metrics.beliefsUpdated} color="#22c55e" sub="auto-learned" />
      </div>

      <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'monospace', marginBottom: 12 }}>Issue breakdown</div>
      <div style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 12, padding: '16px 20px', marginBottom: 20 }}>
        {[
          ['High severity', metrics.highCount, '#f87171', '#2a1010'],
          ['Medium severity', metrics.medCount, '#fbbf24', '#2a1a00'],
          ['Low severity', metrics.lowCount, '#60a5fa', '#0a1020'],
          ['Style', metrics.styleCount, '#a78bfa', '#1a1030'],
          ['Bug', metrics.bugCount, '#f87171', '#2a1010'],
          ['Architecture', metrics.archCount, '#34d399', '#0a2a1a'],
        ].map(([label, val, color, bg]) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: '#4a4a5e', fontFamily: 'monospace', width: 120, flexShrink: 0 }}>{label}</span>
            <div style={{ flex: 1, background: '#0f0f14', borderRadius: 4, height: 8, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 4, background: color,
                width: metrics.totalIssues > 0 ? `${Math.round((val / metrics.totalIssues) * 100)}%` : '0%',
                transition: 'width .5s ease'
              }} />
            </div>
            <span style={{ fontSize: 11, color, fontFamily: 'monospace', width: 24, textAlign: 'right' }}>{val}</span>
          </div>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'monospace', marginBottom: 12 }}>Repos reviewed</div>
      {metrics.repos.length === 0
        ? <div style={{ fontSize: 12, color: '#2a2a3a', fontFamily: 'monospace' }}>No reviews yet.</div>
        : metrics.repos.map((r, i) => (
          <div key={i} style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 10, padding: '10px 14px', marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: '#bbb', fontFamily: 'monospace' }}>{r.repo} PR #{r.pr}</span>
            <div style={{ display: 'flex', gap: 6 }}>
              {r.high > 0 && <span style={{ background: '#2a1010', color: '#f87171', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace' }}>{r.high} high</span>}
              {r.med > 0 && <span style={{ background: '#2a1a00', color: '#fbbf24', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace' }}>{r.med} med</span>}
              {r.high === 0 && r.med === 0 && <span style={{ background: '#0a2a1a', color: '#34d399', fontSize: 10, padding: '2px 7px', borderRadius: 4, fontFamily: 'monospace' }}>clean</span>}
            </div>
          </div>
        ))
      }
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('review')
  const [ghRepo, setGhRepo] = useState('')
  const [prNum, setPrNum] = useState('')
  const [postComment, setPostComment] = useState(true)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [typingMsg, setTypingMsg] = useState('')
  const [beliefs, setBeliefs] = useState({ rules: [], past_decisions: [] })
  const [postedSet, setPostedSet] = useState(new Set())
  const [metrics, setMetrics] = useState({
    prsReviewed: 0, totalIssues: 0, highCount: 0, medCount: 0, lowCount: 0,
    styleCount: 0, bugCount: 0, archCount: 0, beliefsUpdated: 0,
    totalConfidence: 0, repos: []
  })
  const chatRef = useRef(null)

  useEffect(() => {
    fetch('/api/beliefs').then(r => r.json()).then(setBeliefs).catch(() => {})
  }, [])

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages, loading])

  const runReview = async () => {
    if (!ghRepo.trim() || !prNum.trim()) return
    setLoading(true)
    setMessages(m => [...m, { type: 'user', repo: ghRepo, pr: prNum }])

    let i = 0
    setTypingMsg(TYPING_MSGS[0])
    const iv = setInterval(() => { i++; if (i < TYPING_MSGS.length) setTypingMsg(TYPING_MSGS[i]) }, 700)

    try {
      const resp = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo: ghRepo.trim(),
          pr_number: parseInt(prNum),
          post_comment: postComment
        }),
      })
      const data = await resp.json()
      clearInterval(iv)
      setLoading(false)
      if (!resp.ok) throw new Error(data.detail || 'Review failed')

      setMessages(m => [...m, { type: 'review', data, idx: m.length + 1 }])

      const issues = data.review?.issues ?? []
      const high = issues.filter(x => x.severity === 'high').length
      const med = issues.filter(x => x.severity === 'medium').length
      const low = issues.filter(x => x.severity === 'low').length
      const totalConf = issues.reduce((s, x) => s + (x.confidence ?? 75), 0)

      setMetrics(prev => ({
        prsReviewed: prev.prsReviewed + 1,
        totalIssues: prev.totalIssues + issues.length,
        highCount: prev.highCount + high,
        medCount: prev.medCount + med,
        lowCount: prev.lowCount + low,
        styleCount: prev.styleCount + issues.filter(x => x.type === 'style').length,
        bugCount: prev.bugCount + issues.filter(x => x.type === 'bug').length,
        archCount: prev.archCount + issues.filter(x => x.type === 'architecture').length,
        beliefsUpdated: prev.beliefsUpdated + (data.beliefs_updated ? 1 : 0),
        totalConfidence: prev.totalConfidence + totalConf,
        repos: [{ repo: ghRepo.trim(), pr: prNum, high, med }, ...prev.repos]
      }))

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

  return (
    <>
      <style>{G}</style>
      <div style={{ height: '100vh', background: '#09090c', display: 'flex', flexDirection: 'column', fontFamily: "'Inter', system-ui, sans-serif", color: '#e4e4f0' }}>

        <div style={{ height: 52, borderBottom: '1px solid #1f1f2e', display: 'flex', alignItems: 'center', padding: '0 20px', flexShrink: 0, background: '#0f0f14' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 28 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#f97316' }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: '#f97316', fontFamily: 'monospace' }}>ReviewAgent</span>
          </div>
          {[['review', 'Review'], ['dashboard', 'Dashboard'], ['rules', 'Rules']].map(([t, label]) => (
            <button key={t} style={navBtn(t)} onClick={() => setTab(t)}>
              {label}
              {t === 'dashboard' && metrics.prsReviewed > 0 && (
                <span style={{ marginLeft: 6, background: '#1f1f2e', color: '#f97316', fontSize: 10, padding: '1px 6px', borderRadius: 10 }}>{metrics.prsReviewed}</span>
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
            <div ref={chatRef} style={{ flex: 1, overflowY: 'auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860, width: '100%', margin: '0 auto', alignSelf: 'center' }}>

              {messages.length === 0 && !loading && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, minHeight: 380 }}>
                  <div style={{ width: 56, height: 56, borderRadius: '50%', border: '1.5px solid #1f1f2e', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'glow 3s ease infinite' }}>
                    <div style={{ width: 20, height: 20, borderRadius: '50%', border: '1.5px solid #2a2a3a' }} />
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 15, color: '#4a4a5e', marginBottom: 6 }}>Enter a GitHub PR to review</div>
                    <div style={{ fontSize: 12, color: '#2a2a3a' }}>I'll fetch the diff and review it against your team's belief system</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                    {['vercel/next.js · 123', 'facebook/react · 456'].map(example => (
                      <button key={example} onClick={() => {
                        const [repo, pr] = example.split(' · ')
                        setGhRepo(repo); setPrNum(pr)
                      }} style={{ background: '#14141c', color: '#3a3a4a', border: '1px solid #1f1f2e', borderRadius: 8, padding: '6px 14px', fontSize: 11, cursor: 'pointer', fontFamily: 'monospace' }}>
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, idx) => {
                if (msg.type === 'user') return (
                  <div key={idx} className="msg" style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{ background: '#1a1a24', border: '1px solid #1f1f2e', borderRadius: '12px 12px 4px 12px', padding: '12px 16px', maxWidth: '75%' }}>
                      <div style={{ fontSize: 10, color: '#2a2a3a', fontFamily: 'monospace', marginBottom: 6 }}>github pr</div>
                      <div style={{ fontSize: 13, color: '#ccc', fontFamily: 'monospace' }}>{msg.repo} <span style={{ color: '#f97316' }}>#{msg.pr}</span></div>
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
                    <button onClick={runReview} style={{ marginLeft: 12, background: 'transparent', color: '#f97316', border: '1px solid rgba(249,115,22,.3)', borderRadius: 6, padding: '3px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit' }}>Retry</button>
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
                <div style={{ background: '#14141c', border: '1px solid #1f1f2e', borderRadius: 12, padding: '14px 16px' }}>
                  <div style={{ fontSize: 10, color: '#2a2a3a', textTransform: 'uppercase', letterSpacing: '1.2px', fontFamily: 'monospace', marginBottom: 10 }}>GitHub PR</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10, marginBottom: 12 }}>
                    <input
                      style={{ background: '#1a1a24', border: '1px solid #1f1f2e', borderRadius: 8, padding: '10px 12px', color: '#ccc', fontSize: 13, fontFamily: 'monospace', width: '100%' }}
                      placeholder="owner/repo  (e.g. Dhruva-Aher/Trial)"
                      value={ghRepo}
                      onChange={e => setGhRepo(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && runReview()}
                    />
                    <input
                      style={{ background: '#1a1a24', border: '1px solid #1f1f2e', borderRadius: 8, padding: '10px 12px', color: '#ccc', fontSize: 13, fontFamily: 'monospace', width: '100%' }}
                      placeholder="PR #"
                      type="number"
                      value={prNum}
                      onChange={e => setPrNum(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && runReview()}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button
                      onClick={runReview}
                      disabled={loading || !ghRepo.trim() || !prNum.trim()}
                      style={{ background: '#f97316', color: '#0c0c0f', border: 'none', borderRadius: 8, padding: '9px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', opacity: (loading || !ghRepo.trim() || !prNum.trim()) ? 0.4 : 1 }}
                    >
                      {loading ? 'Reviewing...' : 'Run review'}
                    </button>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#4a4a5e', cursor: 'pointer', marginLeft: 4 }}>
                      <input type="checkbox" checked={postComment} onChange={e => setPostComment(e.target.checked)} style={{ accentColor: '#f97316' }} />
                      Post to GitHub
                    </label>
                    {metrics.prsReviewed > 0 && (
                      <span style={{ marginLeft: 'auto', fontSize: 11, color: '#2a2a3a', fontFamily: 'monospace' }}>
                        {metrics.prsReviewed} reviewed · {metrics.totalIssues} issues
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'dashboard' && <Dashboard metrics={metrics} />}

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
      </div>
    </>
  )
}
