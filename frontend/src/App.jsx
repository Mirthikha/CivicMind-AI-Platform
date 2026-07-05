import axios from "axios";
import {
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  Building2,
  Check,
  ChevronDown,
  Copy,
  Eye,
  EyeOff,
  FileText,
  Home,
  Link as LinkIcon,
  LogOut,
  MapPin,
  MessageCircle,
  Phone,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  Upload,
  User,
  Zap
} from "lucide-react";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import CrossDeptGraph from './CrossDeptGraph';

const API_BASE = "https://civicmind-ai-platform.onrender.com";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
});

const fallbackComplaints = [
  {
    id: "CM1A2B3C",
    problem: "Large pothole near bus stop causing traffic slowdown",
    location: "Anna Salai, Chennai",
    department: "Roads",
    priority: "high",
    status: "in_progress",
    date: "2026-07-01",
    budget: "Rs. 18,000 - Rs. 25,000",
    explanation: "AI detected road surface damage with commuter safety impact.",
    root_cause: "Likely monsoon water logging and delayed resurfacing.",
    recommended_action: "Patch immediately and schedule resurfacing inspection.",
    departments_involved: ["Roads", "Traffic"]
  },
  {
    id: "CM9D8E7F",
    problem: "Streetlight not working for three nights",
    location: "Indiranagar, Bengaluru",
    department: "Electricity",
    priority: "medium",
    status: "under_review",
    date: "2026-06-29",
    budget: "Rs. 3,000 - Rs. 7,000",
    explanation: "Possible lamp failure or feeder issue.",
    root_cause: "Component wear or local wiring fault.",
    recommended_action: "Dispatch technician for pole inspection.",
    departments_involved: ["Electricity"]
  },
  {
    id: "CM4G5H6I",
    problem: "Water leakage from main pipeline",
    location: "Bandra West, Mumbai",
    department: "Water",
    priority: "critical",
    status: "submitted",
    date: "2026-07-02",
    budget: "Rs. 40,000 - Rs. 65,000",
    explanation: "Urgent water loss and road damage risk identified.",
    root_cause: "Pipeline joint failure.",
    recommended_action: "Isolate valve and repair section.",
    departments_involved: ["Water", "Roads"]
  }
];

const statusColors = {
  submitted: "muted",
  under_review: "info",
  in_progress: "warning",
  resolved: "success",
  disputed: "danger"
};

const statusLabels = {
  submitted: "Submitted",
  under_review: "Under Review",
  in_progress: "In Progress",
  resolved: "Resolved",
  disputed: "Reopened"
};

const priorityLabels = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low"
};

function useStoredUser(key) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key) || "null");
    } catch {
      return null;
    }
  });

  const save = (value) => {
    localStorage.setItem(key, JSON.stringify(value));
    setUser(value);
  };

  const clear = () => {
    localStorage.removeItem(key);
    setUser(null);
  };

  return [user, save, clear];
}

function useAsyncAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async (action) => {
    setLoading(true);
    setError("");
    try {
      return await action();
    } catch (err) {
      const message = err?.response?.data?.message || err?.response?.data?.detail || err.message || "Something went wrong";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { loading, error, setError, run };
}

function App() {
  const [toast, setToast] = useState(null);

  const showToast = (message, type = "success") => {
    setToast({ message, type, id: Date.now() });
  };

  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/citizen/login" element={<CitizenLogin showToast={showToast} />} />
        <Route path="/citizen/register" element={<CitizenRegister showToast={showToast} />} />
        <Route path="/citizen/dashboard" element={<CitizenGuard><CitizenDashboard showToast={showToast} /></CitizenGuard>} />
        <Route path="/citizen/complaint" element={<CitizenGuard><FileComplaint showToast={showToast} /></CitizenGuard>} />
        <Route path="/citizen/track" element={<CitizenGuard><TrackStatus showToast={showToast} /></CitizenGuard>} />
        <Route path="/citizen/ask" element={<CitizenGuard><AskAI showToast={showToast} /></CitizenGuard>} />
        <Route path="/citizen/ratings" element={<CitizenGuard><CitizenRatings showToast={showToast} /></CitizenGuard>} />
        <Route path="/official/login" element={<OfficialLogin showToast={showToast} />} />
        <Route path="/official/dashboard" element={<OfficialGuard><OfficialDashboard /></OfficialGuard>} />
        <Route path="/official/complaints" element={<OfficialGuard><AllComplaints showToast={showToast} /></OfficialGuard>} />
        <Route path="/official/department" element={<OfficialGuard><DepartmentView /></OfficialGuard>} />
        <Route path="/official/alerts" element={<OfficialGuard><CrossDeptAlerts /></OfficialGuard>} />
        <Route path="/official/ratings" element={<OfficialGuard><OfficialRatings /></OfficialGuard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </>
  );
}

function CitizenGuard({ children }) {
  const user = getStorage("civicmind_citizen");
  return user ? children : <Navigate to="/citizen/login" replace />;
}

function OfficialGuard({ children }) {
  const user = getStorage("civicmind_official");
  return user ? children : <Navigate to="/official/login" replace />;
}

function getStorage(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}

function Shell({ type = "citizen", children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [citizen, , clearCitizen] = useStoredUser("civicmind_citizen");
  const [official, , clearOfficial] = useStoredUser("civicmind_official");
  const isOfficial = type === "official";
  const user = isOfficial ? official : citizen;

  // 1. Safe extraction with optional chaining to prevent crash states
  const currentDept = official?.department || "";

  // 2. Build link routing dynamically without broken variables
  const links = isOfficial
    ? [
        ["/official/dashboard", "Dashboard"],
        ["/official/complaints", "Complaints"],
        // Hide the department view tab ONLY for the supervising Admin account
        ...(currentDept && currentDept !== "All Departments" && currentDept !== "All" 
          ? [["/official/department", "Department"]] 
          : []),
        ["/official/alerts", "Alerts"],
        ["/official/ratings", "Ratings"]
      ]
    : [
        ["/citizen/dashboard", "Home"],
        ["/citizen/complaint", "File Complaint"],
        ["/citizen/track", "Track"],
        ["/citizen/ask", "Ask AI"],
        ["/citizen/ratings", "Ratings"]
      ];

  const logout = () => {
    isOfficial ? clearOfficial() : clearCitizen();
    navigate(isOfficial ? "/official/login" : "/citizen/login");
  };

  return (
    <div className="app-shell">
      <nav className="navbar">
        <Link className="brand brand-dark" to={isOfficial ? "/official/dashboard" : "/citizen/dashboard"}>
          <Building2 size={24} /> CivicMind{isOfficial ? " Officials" : ""}
        </Link>
        <div className="nav-links">
          {links.map(([to, label]) => (
            <Link key={to} className={location.pathname === to ? "active" : ""} to={to}>
              {label}
            </Link>
          ))}
        </div>
        <div className="nav-profile">
          <User size={17} />
          <span>{user?.name || "User"}{isOfficial && user?.department ? ` (${user.department})` : ""}</span>
          <button className="icon-btn" onClick={logout} title="Logout">
            <LogOut size={18} />
          </button>
        </div>
      </nav>
      <main className="page-wrap">{children}</main>
    </div>
  );
}

function Landing() {
  return (
    <main className="landing">
      <section className="hero">
        <div className="hero-content">
          <Link className="brand" to="/">
            <Building2 size={32} /> CivicMind
          </Link>
          <h1>AI-Powered Civic Intelligence for Smarter Cities</h1>
          <p>Report issues, track progress, and help build a better community powered by AI.</p>
          <div className="entry-grid">
            <EntryCard
              icon={<User />}
              title="I'm a Citizen"
              text="Report civic issues, track complaints, get AI-powered status updates."
              button="Enter as Citizen"
              to="/citizen/login"
              tone="purple"
            />
            <EntryCard
              icon={<Building2 />}
              title="I'm an Official"
              text="Manage complaints, view AI insights, allocate resources intelligently."
              button="Official Login"
              to="/official/login"
              tone="coral"
            />
          </div>
          <div className="feature-strip">
            <span><Bot size={18} /> AI Root Cause Analysis</span>
            <span><BarChart3 size={18} /> Smart Prioritization</span>
            <span><Sparkles size={18} /> Budget Intelligence</span>
          </div>
        </div>
      </section>
    </main>
  );
}

function EntryCard({ icon, title, text, button, to, tone }) {
  return (
    <article className={`entry-card ${tone}`}>
      <div className="entry-icon">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
      <Link className="button button-white" to={to}>{button}</Link>
    </article>
  );
}

function AuthCard({ title, subtitle, children, dark = false }) {
  return (
    <main className={`auth-page ${dark ? "official-bg" : ""}`}>
      <section className="auth-card">
        <Link className="auth-logo" to="/">
          <Building2 /> CivicMind
        </Link>
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {children}
      </section>
    </main>
  );
}

function CitizenLogin({ showToast }) {
  const navigate = useNavigate();
  const [, saveCitizen] = useStoredUser("civicmind_citizen");
  const { loading, error, run } = useAsyncAction();
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });

  const submit = async (event) => {
    event.preventDefault();
    if (!form.email || !form.password) return;
    await run(async () => {
      const { data } = await api.post("/api/auth/citizen-login", form);
      const user = data.user || data.citizen || data;
      saveCitizen({ id: user.id || user._id || "citizen-demo", name: user.name || "Citizen", email: user.email || form.email, phone: user.phone || "" });
      showToast("Welcome back to CivicMind");
      navigate("/citizen/dashboard");
    });
  };

  return (
    <AuthCard title="Welcome Back!" subtitle="Login to track your complaints">
      <form className="form" onSubmit={submit}>
        <Field icon={<MessageCircle />} placeholder="Email address" type="email" value={form.email} onChange={(email) => setForm({ ...form, email })} />
        <PasswordField value={form.password} onChange={(password) => setForm({ ...form, password })} show={showPassword} setShow={setShowPassword} />
        <button className="button button-primary full" disabled={loading}>{loading ? <Spinner tiny /> : "Login"}</button>
        {error && <Alert message={error} />}
        <p className="auth-switch">Don't have an account? <Link to="/citizen/register">Register here</Link></p>
      </form>
    </AuthCard>
  );
}

function CitizenRegister({ showToast }) {
  const navigate = useNavigate();
  const [, saveCitizen] = useStoredUser("civicmind_citizen");
  const { loading, error, setError, run } = useAsyncAction();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", confirm: "" });

  const submit = async (event) => {
    event.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords do not match");
      return;
    }
    await run(async () => {
      const payload = { name: form.name, email: form.email, phone: form.phone, password: form.password };
      const { data } = await api.post("/api/auth/citizen-register", payload);
      const user = data.user || data.citizen || data;
      saveCitizen({ id: user.id || user._id || "citizen-demo", name: user.name || form.name, email: user.email || form.email, phone: user.phone || form.phone });
      showToast("Your CivicMind account is ready");
      navigate("/citizen/dashboard");
    });
  };

  return (
    <AuthCard title="Join CivicMind" subtitle="Help make your city better">
      <form className="form" onSubmit={submit}>
        <Field icon={<User />} placeholder="Full Name" value={form.name} onChange={(name) => setForm({ ...form, name })} />
        <Field icon={<MessageCircle />} placeholder="Email address" type="email" value={form.email} onChange={(email) => setForm({ ...form, email })} />
        <Field icon={<Phone />} placeholder="Phone Number" value={form.phone} onChange={(phone) => setForm({ ...form, phone })} />
        <Field icon={<ShieldCheck />} placeholder="Password" type="password" value={form.password} onChange={(password) => setForm({ ...form, password })} />
        <Field icon={<ShieldCheck />} placeholder="Confirm Password" type="password" value={form.confirm} onChange={(confirm) => setForm({ ...form, confirm })} />
        <button className="button button-primary full" disabled={loading}>{loading ? <Spinner tiny /> : "Register"}</button>
        {error && <Alert message={error} />}
        <p className="auth-switch">Already have account? <Link to="/citizen/login">Login</Link></p>
      </form>
    </AuthCard>
  );
}

function OfficialLogin({ showToast }) {
  const navigate = useNavigate();
  const [, saveOfficial] = useStoredUser("civicmind_official");
  const { loading, error, run } = useAsyncAction();
  const [form, setForm] = useState({ email: "", password: "" });

  const submit = async (event) => {
  event.preventDefault();
  await run(async () => {
    const { data } = await api.post("/api/auth/official-login", form);
    const user = data.user || data.official || data;
    
    // Explicitly lock in the precise department sent by the backend
    saveOfficial({
      name: user.name || "City Official",
      role: user.role || "official",
      department: user.department,
      email: user.email || form.email
    });
    
    showToast("Officials dashboard unlocked");
    navigate("/official/dashboard");
  });
};

  return (
    <AuthCard title="Officials Portal" subtitle="Authorized personnel only" dark>
      <div className="notice">
        <strong>Test accounts</strong>
        <span>admin@civic / admin123</span>
        <span>water@civic / water123</span>
        <span>roads@civic / roads123</span>
        <span>electric@civic / elec123</span>
      </div>
      <form className="form" onSubmit={submit}>
        <Field icon={<MessageCircle />} placeholder="Email address" value={form.email} onChange={(email) => setForm({ ...form, email })} />
        <Field icon={<ShieldCheck />} placeholder="Password" type="password" value={form.password} onChange={(password) => setForm({ ...form, password })} />
        <button className="button button-dark full" disabled={loading}>{loading ? <Spinner tiny /> : "Access Dashboard"}</button>
        {error && <Alert message={error} />}
      </form>
    </AuthCard>
  );
}

function CitizenDashboard({ showToast }) {
  const citizen = getStorage("civicmind_citizen");
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
  let active = true;
  
  // Safeguard lookup to use your actual contact phone string instead of an auto-generated token ID
  const searchIdentifier = citizen.phone || citizen.id;

  api.get(`/api/auth/citizen-complaints/${searchIdentifier}`)
    .then(({ data }) => active && setComplaints(data.complaints || data || []))
      .catch(() => active && setComplaints(fallbackComplaints.slice(0, 2)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [citizen.id]);

  return (
    <Shell>
      <section className="welcome-banner">
        <h1>Hello, {citizen.name || "Citizen"}!</h1>
        <p>How can we help you today?</p>
      </section>
      <div className="quick-grid">
        <QuickCard icon={<FileText />} title="File a Complaint" to="/citizen/complaint" />
        <QuickCard icon={<Search />} title="Track Status" to="/citizen/track" />
        <QuickCard icon={<MessageCircle />} title="Ask AI" to="/citizen/ask" />
        <QuickCard icon={<Star />} title="Rate Service" to="/citizen/ratings" />
      </div>
      <SectionTitle title="My Recent Complaints" />
      {loading ? <LoadingBlock /> : complaints.length ? (
        <div className="complaint-list">
          {complaints.map((item) => (
            <button key={item.id || item.complaint_id} className="complaint-card" onClick={() => navigate(`/citizen/track?id=${item.id || item.complaint_id}`)}>
              <span className="id-badge">{item.id || item.complaint_id}</span>
              <strong>{item.problem || item.complaint_text || item.summary}</strong>
              <span>{item.department || "General"} Department</span>
              <Badge tone={statusColors[item.status] || "info"}>{statusLabels[item.status] || item.status || "Submitted"}</Badge>
              <small>{item.date || item.created_at || "Today"}</small>
            </button>
          ))}
        </div>
      ) : <EmptyState />}
    </Shell>
  );
}

function FileComplaint({ showToast }) {
  const citizen = getStorage("civicmind_citizen");
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: citizen.name || "", phone: citizen.phone || "", location: "", description: "" });
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState(0);
  const [result, setResult] = useState(null);
  const messages = ["Classifying issue type...", "Finding related complaints...", "Generating root cause analysis...", "Estimating budget...", "Creating official explanation..."];

  useEffect(() => {
    if (!loading) return;
    const timer = setInterval(() => setLoadingMessage((value) => (value + 1) % messages.length), 1800);
    return () => clearInterval(timer);
  }, [loading]);

  const pickImage = (file) => {
    setImage(file);
    setPreview(file ? URL.createObjectURL(file) : "");
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    const body = new FormData();
    body.append("complaint_text", form.description);
    body.append("location", form.location);
    body.append("citizen_name", form.name);
    body.append("citizen_contact", form.phone);
    if (image) body.append("image", image);
    try {
      const { data } = await api.post("/api/complaints/submit", body, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(normalizeSubmission(data));
      showToast("Complaint submitted successfully");
    } catch {
      setResult(normalizeSubmission({}));
      showToast("Backend unavailable, showing demo submission", "error");
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <Shell>
        <section className="success-panel">
          <div className="success-check"><Check size={46} /></div>
          <h1>Complaint Submitted Successfully!</h1>
          <div className="id-copy-card">
            <span>Your Complaint ID</span>
            <strong>{result.id}</strong>
            <button className="icon-btn" onClick={() => navigator.clipboard?.writeText(result.id)} title="Copy complaint ID"><Copy size={18} /></button>
            <small>Save this ID to track your complaint</small>
          </div>
          <article className="analysis-card">
            <h2><Bot /> AI Analysis</h2>
            <div className="badge-row">
              <Badge tone="info">{result.department}</Badge>
              <Badge tone={priorityTone(result.priority)}>{priorityLabels[result.priority] || result.priority}</Badge>
            </div>
            <p><strong>What we found:</strong> {result.explanation}</p>
            <p><strong>Budget Estimate:</strong> {result.budget_range}</p>
            <p><strong>Response Target:</strong> {result.response_time}</p>
          </article>
          <div className="action-row">
            <button className="button button-primary" onClick={() => navigate(`/citizen/track?id=${result.id}`)}>Track This Complaint</button>
            <button className="button button-soft" onClick={() => setResult(null)}>File Another</button>
          </div>
        </section>
      </Shell>
    );
  }

  return (
    <Shell>
      <PageHeader title="Report a Civic Issue" subtitle="Our AI will analyze and prioritize your complaint" />
      <form className="card form complaint-form" onSubmit={submit}>
        <Field icon={<User />} placeholder="Full Name" value={form.name} onChange={(name) => setForm({ ...form, name })} />
        <Field icon={<Phone />} placeholder="Contact Number" value={form.phone} onChange={(phone) => setForm({ ...form, phone })} />
        <Field icon={<MapPin />} placeholder="Location" value={form.location} onChange={(location) => setForm({ ...form, location })} />
        <label className="textarea-field">
          <textarea required placeholder="Describe the issue in detail..." value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        <label className="upload-box">
          <input type="file" accept="image/*" onChange={(event) => pickImage(event.target.files?.[0])} />
          {preview ? <img src={preview} alt="Complaint preview" /> : <><Upload size={28} /> Click to upload or drag photo here</>}
        </label>
        <button className="button button-primary full" disabled={loading}>{loading ? "AI is analyzing..." : "Submit Complaint"}</button>
        {loading && (
          <div className="ai-loading">
            <Spinner />
            <strong>AI is analyzing your complaint...</strong>
            <span>This takes about 10-15 seconds</span>
            <p>{messages[loadingMessage]}</p>
          </div>
        )}
      </form>
    </Shell>
  );
}

function normalizeSubmission(data) {
  const analysis = data.ai_analysis || data.analysis || data;
  return {
    id: data.complaint_id || data.id || `CM${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
    department: analysis.department || "Roads Department",
    priority: (analysis.priority || "high").toLowerCase(),
    explanation: analysis.explanation || "The issue appears to need coordinated inspection and timely field response.",
    budget_range: analysis.budget_range || "Rs. 15,000 - Rs. 30,000",
    response_time: analysis.response_time || "24-48 hours"
  };
}

function TrackStatus({ showToast }) {
  const [params] = useSearchParams();
  const initialId = params.get("id") || "";
  const [complaintId, setComplaintId] = useState(initialId);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");

  const track = async (event) => {
    event?.preventDefault();
    if (!complaintId) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/api/complaints/status/${complaintId}`);
      setResult(data.complaint || data);
    } catch {
      setResult({ ...fallbackComplaints[0], id: complaintId, status: complaintId === "RESOLVED" ? "resolved" : "in_progress", updates: demoUpdates });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialId) track();
  }, []);

  const submitFeedback = async () => {
    await api.post("/api/feedback/submit", { complaint_id: complaintId, rating, comment }).catch(() => null);
    showToast("Thanks for sharing your experience");
    setComment("");
    setRating(0);
  };

  return (
    <Shell>
      <PageHeader title="Track Your Complaint" subtitle="Enter your complaint ID for live updates" />
      <form className="search-card" onSubmit={track}>
        <Field icon={<Search />} placeholder="e.g. CM1A2B3C" value={complaintId} onChange={setComplaintId} />
        <button className="button button-primary" disabled={loading}>{loading ? <Spinner tiny /> : "Track Now"}</button>
      </form>
      {result && (
        <article className="card status-card">
          <Badge tone={statusColors[result.status] || "warning"} big>{statusLabels[result.status] || result.status}</Badge>
          <div className="meta-grid">
            <span><strong>Department</strong><Badge tone="info">{result.department}</Badge></span>
            <span><strong>Priority</strong><Badge tone={priorityTone(result.priority)}>{priorityLabels[result.priority] || result.priority}</Badge></span>
            <span><strong>Filed on</strong>{result.date || result.created_at || "Today"}</span>
          </div>
          <Timeline 
  updates={
    result.progress_updates && result.progress_updates.length > 0 
      ? result.progress_updates 
      : [{ timestamp: "Today", note: result.message || "Complaint received and is being reviewed." }]
  } 
/>
          {result.status === "resolved" && (
            <div className="feedback-box">
              <h3>Was your issue resolved? Rate us!</h3>
              <StarPicker value={rating} onChange={setRating} />
              <textarea placeholder="Share a quick comment..." value={comment} onChange={(event) => setComment(event.target.value)} />
              <button className="button button-primary" onClick={submitFeedback}>Submit feedback</button>
            </div>
          )}
        </article>
      )}
    </Shell>
  );
}

const demoUpdates = [
  { timestamp: "Today, 10:30 AM", note: "Field team assigned and route planned." },
  { timestamp: "Yesterday, 5:15 PM", note: "Department accepted the complaint for action." },
  { timestamp: "Yesterday, 2:40 PM", note: "Complaint received and prioritized by AI." }
];

function AskAI({ showToast }) {
  const [messages, setMessages] = useState([
    { from: "ai", text: "Hello! I'm CivicMind AI. I can answer questions about city services, help you understand your complaint status, and guide you through our platform. What would you like to know?", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }
  ]);
  const [question, setQuestion] = useState("");
  const [complaintId, setComplaintId] = useState("");
  const [loading, setLoading] = useState(false);
  const chatRef = useRef(null);
  const suggestions = ["How long does pothole repair take?", "How to get water connection?", "What is an emergency?", "How to track my complaint?", "What is CivicMind?"];

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async () => {
  if (!question.trim()) return;
  const userMessage = { from: "user", text: question, time: nowTime() };
  setMessages((items) => [...items, userMessage]);
  setQuestion("");
  setLoading(true);
  try {
    const formData = new FormData();
    formData.append("question", question);
    if (complaintId) formData.append("complaint_id", complaintId);

    const { data } = await api.post("/api/query", formData, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    setMessages((items) => [...items, { from: "ai", text: data.answer || data.response || "I found that information for you.", time: nowTime() }]);
  } catch {
    setMessages((items) => [...items, { from: "ai", text: "Based on CivicMind guidance, routine civic complaints are reviewed by the relevant department.", time: nowTime() }]);
  } finally {
    setLoading(false);
  }
};

  return (
    <Shell>
      <PageHeader title="Ask CivicMind AI" subtitle="Get instant answers about city services" />
      <div className="chips">{suggestions.map((item) => <button key={item} onClick={() => setQuestion(item)}>{item}</button>)}</div>
      <section className="chat-layout">
        <div className="complaint-id-mini">
          <span>Have a complaint ID?</span>
          <input placeholder="CM1A2B3C" value={complaintId} onChange={(event) => setComplaintId(event.target.value)} />
          <button className="button button-soft">Use</button>
        </div>
        <div className="chat-area" ref={chatRef}>
          {messages.map((message, index) => <ChatBubble key={index} message={message} />)}
          {loading && <ChatBubble message={{ from: "ai", text: "Thinking through your civic query...", time: nowTime() }} loading />}
        </div>
        <div className="chat-input">
          <input placeholder="Type your question..." value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => event.key === "Enter" && send()} />
          <button className="round-send" onClick={send} title="Send"><Send size={20} /></button>
        </div>
      </section>
    </Shell>
  );
}

function CitizenRatings({ showToast }) {
  const citizen = getStorage("civicmind_citizen");
  const [ratings, setRatings] = useState(defaultRatings);
  const [form, setForm] = useState({ complaint_id: "", rating: 0, comment: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/api/feedback/ratings")
      .then(({ data }) => {
        // Safely check if data.ratings is the actual list array
        if (data && Array.isArray(data.ratings)) {
          setRatings(data.ratings);
        } else if (Array.isArray(data)) {
          setRatings(data);
        } else {
          setRatings(defaultRatings);
        }
      })
      .catch(() => setRatings(defaultRatings));
  }, []);

  const submit = async () => {
    if (!form.complaint_id || !form.rating) {
      showToast("Add a complaint ID and star rating first", "error");
      return;
    }
    setLoading(true);
    const formData = new FormData();
    formData.append("complaint_id", form.complaint_id);
    formData.append("rating", form.rating);
    formData.append("comment", form.comment);
    formData.append("citizen_name", citizen?.name || "Anonymous Citizen");

    try {
      await api.post("/api/feedback/submit", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      showToast("Thanks for sharing your experience");
      setForm({ complaint_id: "", rating: 0, comment: "" });
    } catch {
      showToast("Couldn't submit feedback right now", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Shell>
      <PageHeader title="Service Ratings" subtitle="See how our city departments are performing" />
      <div className="rating-grid">
        {ratings.map((dept) => <RatingCard key={dept.department} dept={dept} />)}
      </div>
      <section className="card feedback-box">
        <h2>Had a complaint resolved? Share your experience!</h2>
        <Field icon={<FileText />} placeholder="Complaint ID" value={form.complaint_id} onChange={(complaint_id) => setForm({ ...form, complaint_id })} />
        <StarPicker value={form.rating} onChange={(rating) => setForm({ ...form, rating })} />
        <textarea placeholder="Tell us what worked well or what can improve..." value={form.comment} onChange={(event) => setForm({ ...form, comment: event.target.value })} />
        <button className="button button-primary" onClick={submit} disabled={loading}>{loading ? <Spinner tiny /> : "Submit"}</button>
      </section>
    </Shell>
  );
}

const defaultRatings = [
  { department: "Water Department", icon: "water", rating: 4.2, responses: 218, comments: ["Quick valve repair", "Helpful updates"] },
  { department: "Roads Department", icon: "roads", rating: 3.9, responses: 184, comments: ["Pothole fixed in two days", "Needs faster resurfacing"] },
  { department: "Electricity Department", icon: "electric", rating: 4.5, responses: 261, comments: ["Streetlight repaired", "Clear communication"] }
];

function OfficialDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

 useEffect(() => {
  api.get("/api/officials/dashboard")
    .then(({ data }) => {
      // If the backend has true data, parse it; otherwise default arrays cleanly
      setData({
        complaints: data?.all_complaints || [],
        emergencies: data?.emergencies || [],
        stats: data?.stats || {}
      });
    })
    .catch(() => {
      // In case of an unexpected dropout, keep the UI clean with no fake alerts
      setData({
        complaints: [],
        emergencies: [],
        stats: {}
      });
    })
    .finally(() => setLoading(false));
}, []);

  if (loading) return <Shell type="official"><LoadingBlock /></Shell>;

  const emergencies = data.complaints.filter((item) => item.priority === "critical");
  const statusData = Object.entries(groupCount(data.complaints, "status")).map(([name, value]) => ({ name: statusLabels[name] || name, value }));
  const deptData = Object.entries(groupCount(data.complaints, "department")).map(([department, count]) => ({ department, count }));

  return (
    <Shell type="official">
      {emergencies.length > 0 && (
        <section className="emergency-banner">
          <AlertTriangle /> <strong>{emergencies.length} Active Emergency Alerts</strong>
          <span>{emergencies.map((item) => item.id).join(", ")}</span>
        </section>
      )}
      <div className="stats-grid">
        <StatCard title="Total Complaints" value={data.complaints.length} tone="purple" />
        <StatCard title="Emergencies" value={emergencies.length} tone="red" />
        <StatCard title="Critical" value={data.complaints.filter((item) => ["critical", "high"].includes(item.priority)).length} tone="orange" />
        <StatCard title="Total Budget Range" value="Rs. 1.2L+" tone="green" />
      </div>
      <div className="chart-grid">
        <ChartCard title="Complaints by Status">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={88}>
                {statusData.map((_, index) => <Cell key={index} fill={["#6C63FF", "#74B9FF", "#FFB347", "#43D9A2", "#FF6B6B"][index % 5]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Complaints by Department">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={deptData}>
              <XAxis dataKey="department" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#6C63FF" radius={[12, 12, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </Shell>
  );
}

function AllComplaints({ showToast }) {
  const official = getStorage("civicmind_official");
  const [complaints, setComplaints] = useState([]);
  const [filters, setFilters] = useState({ department: "", priority: "", status: "", q: "" });
  const [expanded, setExpanded] = useState("");
  const [modal, setModal] = useState(null);

  useEffect(() => {
    api.get("/api/complaints/all")
      .then(({ data }) => setComplaints(data.complaints || data || []))
      .catch(() => setComplaints(fallbackComplaints));
  }, []);

  const filtered = complaints.filter((item) => {
    const text = `${item.id} ${item.problem} ${item.location}`.toLowerCase();
    return (!filters.department || item.department === filters.department)
      && (!filters.priority || item.priority === filters.priority)
      && (!filters.status || item.status === filters.status)
      && (!filters.q || text.includes(filters.q.toLowerCase()));
  });

  const updateStatus = async (payload) => {
  const formData = new FormData();
  formData.append("complaint_id", payload.complaint_id);
  formData.append("new_status", payload.status); // backend uses 'new_status'
  formData.append("update_note", payload.note);   // backend uses 'update_note'
  formData.append("updated_by", official.name);  // backend uses 'updated_by'

  await api.post("/api/officials/update-status", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  }).catch(() => null);

  setComplaints((items) => items.map((item) => item.id === payload.complaint_id ? { ...item, status: payload.status } : item));
  setModal(null);
  showToast("Complaint status updated");
};

  return (
    <Shell type="official">
      <PageHeader title="Complaint Management" subtitle="Filter, inspect, and update AI-prioritized complaints" />
      <FilterBar filters={filters} setFilters={setFilters} />
      <ComplaintTable complaints={filtered} expanded={expanded} setExpanded={setExpanded} onUpdate={setModal} />
      {modal && <StatusModal complaint={modal} onClose={() => setModal(null)} onSave={updateStatus} />}
    </Shell>
  );
}

function DepartmentView() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Force a direct synchronous check from disk so state cannot flash null
    const freshUserData = JSON.parse(localStorage.getItem("civicmind_official") || "{}");
    const deptName = freshUserData?.department || "";
    
    if (!deptName) {
      setLoading(false);
      return;
    }

    // 2. Extract clean name for API filtering
    const cleanDept = deptName.replace(" Department", "");

    api.get(`/api/complaints/department/${cleanDept}`)
      .then(({ data }) => {
        setComplaints(data.complaints || []);
      })
      .catch(() => {
        const localFilter = fallbackComplaints.filter(
          (item) => item.department === cleanDept || cleanDept === "All Departments" || cleanDept === "All"
        );
        setComplaints(localFilter);
      })
      .finally(() => setLoading(false));
  }, []); // Strictly empty dependency array—nothing hanging or broken!

  return (
    <Shell type="official">
      <PageHeader title="Department Queue" subtitle="Focused workflow list" />
      {loading ? (
        <LoadingBlock />
      ) : complaints.length > 0 ? (
        <ComplaintTable complaints={complaints} compact={false} />
      ) : (
        <EmptyState title="Queue clear!" subtext="No outstanding issues assigned to this sector." />
      )}
    </Shell>
  );
}
function CrossDeptAlerts() {
  return (
    <Shell type="official">
      <PageHeader 
        title="Cross-Department Intelligence Graph" 
        subtitle="AI-detected asset intersections sharing an underlying root cause infrastructure issue" 
      />
      <div style={{ background: 'white', padding: '24px', borderRadius: '16px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', marginTop: '20px' }}>
        <CrossDeptGraph />
      </div>
    </Shell>
  );
}

function OfficialRatings() {
  return (
    <Shell type="official">
      <PageHeader title="Performance Ratings" subtitle="Department-wise service satisfaction" />
      <div className="rating-grid">{defaultRatings.map((dept) => <RatingCard key={dept.department} dept={dept} />)}</div>
    </Shell>
  );
}

function Field({ icon, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="input-field">
      {icon}
      <input required type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function PasswordField({ value, onChange, show, setShow }) {
  return (
    <label className="input-field">
      <ShieldCheck />
      <input required type={show ? "text" : "password"} value={value} placeholder="Password" onChange={(event) => onChange(event.target.value)} />
      <button type="button" className="bare-btn" onClick={() => setShow(!show)}>{show ? <EyeOff /> : <Eye />}</button>
    </label>
  );
}

function Alert({ message }) {
  return <div className="alert"><AlertTriangle size={18} /> {message}</div>;
}

function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [toast, onClose]);
  if (!toast) return null;
  return <div className={`toast ${toast.type}`}>{toast.type === "error" ? <AlertTriangle /> : <Check />} {toast.message}</div>;
}

function Spinner({ tiny = false }) {
  return <span className={`spinner ${tiny ? "tiny" : ""}`} />;
}

function LoadingBlock() {
  return <div className="loading-block"><Spinner /><span>Please wait...</span></div>;
}

function EmptyState({ icon = <Sparkles />, title = "Nothing here yet", subtext = "New updates will appear here when available." }) {
  return <div className="empty-state">{icon}<h3>{title}</h3><p>{subtext}</p></div>;
}

function Badge({ tone = "info", children, big = false }) {
  return <span className={`badge ${tone} ${big ? "big" : ""}`}>{children}</span>;
}

function priorityTone(priority) {
  return ({ critical: "danger", high: "warning", medium: "yellow", low: "success" })[priority] || "info";
}

function PageHeader({ title, subtitle }) {
  return <header className="page-header"><h1>{title}</h1><p>{subtitle}</p></header>;
}

function SectionTitle({ title }) {
  return <h2 className="section-title">{title}</h2>;
}

function QuickCard({ icon, title, to }) {
  return <Link className="quick-card" to={to}>{icon}<strong>{title}</strong></Link>;
}

function Timeline({ updates }) {
  return (
    <div className="timeline">
      {updates.map((update, index) => (
        <div className="timeline-item" key={index}>
          <span />
          <div><strong>{update.timestamp || update.created_at}</strong><p>{update.note || update.message}</p></div>
        </div>
      ))}
    </div>
  );
}

function StarPicker({ value, onChange }) {
  return <div className="stars">{[1, 2, 3, 4, 5].map((star) => <button key={star} onClick={() => onChange(star)} className={star <= value ? "filled" : ""}><Star fill="currentColor" /></button>)}</div>;
}

function ChatBubble({ message, loading = false }) {
  return (
    <div className={`chat-bubble ${message.from}`}>
      <div className="avatar">{message.from === "ai" ? <Bot /> : <User />}</div>
      <div className="bubble">
        {loading ? <span className="typing"><span /><span /><span /></span> : message.text}
        <small>{message.time}</small>
      </div>
    </div>
  );
}

function RatingCard({ dept }) {
  return (
    <article className="rating-card">
      <div className="dept-icon">{dept.icon === "water" ? "💧" : dept.icon === "roads" ? "🛣️" : "⚡"}</div>
      <h3>{dept.department}</h3>
      <StarDisplay value={dept.rating} />
      <strong>{dept.rating} / 5.0</strong>
      <span>{dept.responses} responses</span>
      <p>{dept.comments?.join(" • ")}</p>
    </article>
  );
}

function StarDisplay({ value }) {
  return <div className="star-display">{[1, 2, 3, 4, 5].map((star) => <Star key={star} fill={star <= Math.round(value) ? "currentColor" : "none"} />)}</div>;
}

function normalizeDashboard(data) {
  const complaints = data.complaints || data.recent_urgent || fallbackComplaints;
  return { ...data, complaints };
}

function groupCount(items, key) {
  return items.reduce((acc, item) => {
    const value = item[key] || "Unknown";
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
}

function StatCard({ title, value, tone }) {
  return <article className={`stat-card ${tone}`}><span>{title}</span><strong>{value}</strong></article>;
}

function ChartCard({ title, children }) {
  return <article className="card chart-card"><h3>{title}</h3>{children}</article>;
}

function ComplaintTable({ complaints, expanded, setExpanded, onUpdate, compact = false }) {
  return (
    <div className="table-card">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Problem</th><th>Location</th><th>Dept</th><th>Priority</th><th>Budget</th><th>Status</th>{!compact && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {complaints.map((item) => (
            <Fragment key={item.id}>
              <tr>
                <td><span className="id-badge">{item.id}</span></td>
                <td>{item.problem}</td>
                <td>{item.location}</td>
                <td><Badge tone="info">{item.department}</Badge></td>
                <td><Badge tone={priorityTone(item.priority)}>{priorityLabels[item.priority] || item.priority}</Badge></td>
                <td>{item.budget}</td>
                <td><Badge tone={statusColors[item.status] || "muted"}>{statusLabels[item.status] || item.status}</Badge></td>
                {!compact && <td><button className="button button-soft small" onClick={() => onUpdate ? onUpdate(item) : setExpanded(expanded === item.id ? "" : item.id)}>Update Status</button></td>}
              </tr>
              {!compact && expanded === item.id && (
                <tr className="expand-row">
                  <td colSpan="8">
                    <p><strong>AI explanation:</strong> {item.explanation}</p>
                    <p><strong>Root cause hypothesis:</strong> {item.root_cause}</p>
                    <p><strong>Recommended action:</strong> {item.recommended_action}</p>
                    <p><strong>Departments involved:</strong> {item.departments_involved?.join(", ")}</p>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FilterBar({ filters, setFilters }) {
  return (
    <div className="filter-bar">
      <Select label="Department" value={filters.department} onChange={(department) => setFilters({ ...filters, department })} options={["", "Water", "Roads", "Electricity"]} />
      <Select label="Priority" value={filters.priority} onChange={(priority) => setFilters({ ...filters, priority })} options={["", "critical", "high", "medium", "low"]} />
      <Select label="Status" value={filters.status} onChange={(status) => setFilters({ ...filters, status })} options={["", "submitted", "under_review", "in_progress", "resolved", "disputed"]} />
      <input placeholder="Search complaints..." value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
    </div>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="select-field">
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option} value={option}>{option || label}</option>)}
      </select>
      <ChevronDown size={16} />
    </label>
  );
}

function StatusModal({ complaint, onClose, onSave }) {
  const [status, setStatus] = useState(complaint.status);
  const [note, setNote] = useState("");
  return (
    <div className="modal-backdrop">
      <div className="modal card">
        <h2>Update Status</h2>
        <p>{complaint.id} - {complaint.problem}</p>
        <Select label="Status" value={status} onChange={setStatus} options={["submitted", "under_review", "in_progress", "resolved", "disputed"]} />
        <textarea placeholder="Add official note..." value={note} onChange={(event) => setNote(event.target.value)} />
        <div className="action-row">
          <button className="button button-soft" onClick={onClose}>Cancel</button>
          <button className="button button-primary" onClick={() => onSave({ complaint_id: complaint.id, status, note })}>Save</button>
        </div>
      </div>
    </div>
  );
}

function LinkedAlert({ alert }) {
  return (
    <article className="linked-alert">
      <div className="linked-main">
        <h2><LinkIcon /> Linked Complaints</h2>
        <p>{alert.root_cause}</p>
        <div className="confidence"><span style={{ width: `${alert.confidence || 75}%` }} /></div>
        <div className="badge-row">{alert.departments?.map((dept) => <Badge key={dept} tone="info">{dept}</Badge>)}</div>
        <strong>{alert.recommended_action}</strong>
      </div>
      <div className="linked-cards">
        {(alert.linked_complaints || []).map((item) => (
          <div className="linked-small" key={item.id}>
            <span>{item.id}</span>
            <p>{item.problem}</p>
          </div>
        ))}
      </div>
    </article>
  );
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default App;
