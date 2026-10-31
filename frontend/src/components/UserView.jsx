import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function UsersView({ me }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ username: "", full_name: "", password: "", role: "clinician" });
  const [msg, setMsg] = useState("");

  const load = () => api.users().then(setUsers).catch((e) => setMsg(e.message));
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setMsg("");
    try {
      await api.createUser({ ...form, full_name: form.full_name || null });
      setForm({ username: "", full_name: "", password: "", role: "clinician" });
      setMsg("User created.");
      load();
    } catch (e) { setMsg(e.message); }
  }

  async function patch(u, change, label) {
    setMsg("");
    try { await api.updateUser(u.id, change); setMsg(label); load(); } catch (e) { setMsg(e.message); }
  }

  return (
    <main className="audit-page">
      <div className="audit-tools"><h2>Users</h2>{msg && <span className="muted small">{msg}</span>}</div>
      <form className="user-form" onSubmit={create}>
        <input placeholder="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <input placeholder="full name (optional)" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <input type="password" placeholder="initial password (8+ chars)" value={form.password}
               onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          <option value="clinician">clinician</option><option value="admin">admin</option>
        </select>
        <button className="primary" disabled={!form.username || form.password.length < 8}>Add user</button>
      </form>
      <div className="table-wrap">
        <table>
          <thead><tr><th>User</th><th>Name</th><th>Role</th><th>Status</th><th>Last login</th><th /></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td className="mono">{u.username}</td>
                <td>{u.full_name || "—"}</td>
                <td>
                  <select value={u.role} disabled={u.id === me.id}
                          onChange={(e) => patch(u, { role: e.target.value }, `Role of ${u.username} changed.`)}>
                    <option value="clinician">clinician</option><option value="admin">admin</option>
                  </select>
                </td>
                <td className={u.is_active ? "ok" : "error"}>{u.is_active ? "active" : "disabled"}</td>
                <td className="mono small">{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "never"}</td>
                <td>
                  {u.id !== me.id && (
                    <button className="ghost small" onClick={() => patch(u, { is_active: !u.is_active },
                      `${u.username} ${u.is_active ? "disabled and signed out" : "re-enabled"}.`)}>
                      {u.is_active ? "Disable" : "Enable"}
                    </button>
                  )}{" "}
                  <button className="ghost small" onClick={() => {
                    const p = window.prompt(`New password for ${u.username} (8+ characters):`);
                    if (p) patch(u, { password: p }, `Password reset; ${u.username} signed out everywhere.`);
                  }}>Reset password</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
