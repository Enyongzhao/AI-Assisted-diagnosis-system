// design_doc §4.4 — Admin-only user management
// Supports: list, search, create, edit (including password reset), deactivate.
// Excludes admin-role accounts from the list — admin manages clinicians and clients only.
import { useState, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  type ManagedUser,
  type CreateUserPayload,
  type UpdateUserPayload,
} from '../api/usersApi'
import { createPatient } from '../api/patientApi'
import { useAuth } from '../context/AuthContext'

type FormMode = 'add' | 'edit'

interface UserForm {
  username: string
  email: string
  password: string
  role: 'clinician' | 'client'
  // Patient profile fields — only required when role === 'client'
  patientName: string
  dateOfBirth: string
  gender: 'male' | 'female' | 'other'
}

const EMPTY_FORM: UserForm = {
  username: '', email: '', password: '', role: 'clinician',
  patientName: '', dateOfBirth: '', gender: 'male',
}

const PAGE_SIZE = 5

export default function AdminPage() {
  const { logout } = useAuth()

  const [users, setUsers] = useState<ManagedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [inputValue, setInputValue] = useState('')
  const [activeQuery, setActiveQuery] = useState('')
  const [page, setPage] = useState(1)

  // Form state
  const [formMode, setFormMode] = useState<FormMode>('add')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<UserForm>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [formLoading, setFormLoading] = useState(false)

  // Confirm delete
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  // Global error/success banner
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  function showBanner(type: 'success' | 'error', msg: string) {
    setBanner({ type, msg })
    setTimeout(() => setBanner(null), 3500)
  }

  async function loadUsers() {
    try {
      const data = await listUsers()
      // Exclude admin-role accounts — admin only manages clinicians and clients
      setUsers(data.filter(u => u.role !== 'admin'))
    } catch {
      showBanner('error', 'Failed to load users.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadUsers() }, [])

  // ── Search ────────────────────────────────────────────────────────────────
  function handleSearch() {
    setActiveQuery(inputValue)
    setPage(1)
  }

  function handleSearchKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleSearch()
  }

  const filtered = users.filter(u =>
    activeQuery === '' ||
    u.username.toLowerCase().includes(activeQuery.toLowerCase()) ||
    u.email.toLowerCase().includes(activeQuery.toLowerCase()) ||
    u.role.toLowerCase().includes(activeQuery.toLowerCase())
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const displayed = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // ── Open form ─────────────────────────────────────────────────────────────
  function openAdd() {
    setFormMode('add')
    setEditingId(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setShowForm(true)
  }

  function openEdit(user: ManagedUser) {
    setFormMode('edit')
    setEditingId(user.id)
    // user.role is always 'clinician'|'client' here (admin rows are filtered from the list)
    // Patient fields are not editable in edit mode — patient profile is managed separately.
    setForm({ username: user.username, email: user.email, password: '', role: user.role as 'clinician' | 'client', patientName: '', dateOfBirth: '', gender: 'male' })
    setFormError(null)
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setFormError(null)
  }

  // ── Submit form ───────────────────────────────────────────────────────────
  async function handleFormSubmit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    setFormLoading(true)
    try {
      if (formMode === 'add') {
        const newUser = await createUser({
          username: form.username,
          email: form.email,
          password: form.password,
          role: form.role,
        } as CreateUserPayload)

        // For client users, also create the linked Patient record (the "registration" step).
        // This sets Patient.linked_user so the client can view their own diagnoses later.
        if (form.role === 'client') {
          await createPatient({
            name: form.patientName,
            date_of_birth: form.dateOfBirth,
            gender: form.gender,
            contact_email: form.email || undefined,
            linked_user: newUser.id,
          })
        }

        showBanner('success', `User "${form.username}" created${form.role === 'client' ? ' with patient profile' : ''}.`)
      } else if (editingId !== null) {
        const payload: UpdateUserPayload = {
          username: form.username,
          email: form.email,
          role: form.role,
        }
        if (form.password) payload.password = form.password
        await updateUser(editingId, payload)
        showBanner('success', `User "${form.username}" updated.`)
      }
      closeForm()
      await loadUsers()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data
      if (data) {
        const msg = Object.entries(data)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join(' | ')
        setFormError(msg)
      } else {
        setFormError('Operation failed. Please try again.')
      }
    } finally {
      setFormLoading(false)
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────────
  async function handleDelete(id: number) {
    try {
      await deleteUser(id)
      setConfirmDeleteId(null)
      showBanner('success', 'User deactivated.')
      await loadUsers()
    } catch {
      showBanner('error', 'Failed to deactivate user.')
    }
  }

  function field(key: keyof UserForm, value: string) {
    setForm(f => ({ ...f, [key]: value }))
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={s.page}>
      {/* Nav */}
      <header style={s.nav}>
        <span style={s.navTitle}>AI Diagnosis System — Admin</span>
        <button style={s.logoutBtn} onClick={logout}>Logout</button>
      </header>

      <main style={s.main}>
        {/* Banner */}
        {banner && (
          <div style={banner.type === 'success' ? s.successBox : s.errorBox}>
            {banner.msg}
          </div>
        )}

        <div style={s.topRow}>
          <h2 style={s.heading}>User Management</h2>
          <button style={s.addBtn} onClick={openAdd}>+ Add User</button>
        </div>

        {/* Add / Edit form */}
        {showForm && (
          <div style={s.formCard}>
            <h3 style={s.formTitle}>
              {formMode === 'add' ? 'Add New User' : `Edit User #${editingId}`}
            </h3>
            {formError && <div style={s.errorBox}>{formError}</div>}
            <form onSubmit={handleFormSubmit} style={s.form}>
              <div style={s.row}>
                <FormField label="Username">
                  <input
                    style={s.input} required value={form.username}
                    onChange={e => field('username', e.target.value)}
                  />
                </FormField>
                <FormField label="Email">
                  <input
                    style={s.input} type="email" required value={form.email}
                    onChange={e => field('email', e.target.value)}
                  />
                </FormField>
              </div>
              <div style={s.row}>
                <FormField label={formMode === 'add' ? 'Password' : 'New Password (leave blank to keep)'}>
                  <input
                    style={s.input} type="password" required={formMode === 'add'}
                    value={form.password}
                    onChange={e => field('password', e.target.value)}
                    placeholder={formMode === 'edit' ? 'Leave blank to keep current' : ''}
                  />
                </FormField>
                <FormField label="Role">
                  <select
                    style={s.input} value={form.role}
                    onChange={e => field('role', e.target.value as UserForm['role'])}
                  >
                    <option value="clinician">Clinician</option>
                    <option value="client">Client</option>
                  </select>
                </FormField>
              </div>
              {/* Patient profile — only shown when creating a new client user */}
              {formMode === 'add' && form.role === 'client' && (
                <>
                  <div style={s.sectionDivider}>
                    Patient Profile <span style={s.sectionHint}>(linked to this account)</span>
                  </div>
                  <div style={s.row}>
                    <FormField label="Patient Full Name">
                      <input
                        style={s.input} required value={form.patientName}
                        onChange={e => field('patientName', e.target.value)}
                        placeholder="As it appears on ID"
                      />
                    </FormField>
                    <FormField label="Date of Birth">
                      <input
                        style={s.input} type="date" required value={form.dateOfBirth}
                        onChange={e => field('dateOfBirth', e.target.value)}
                      />
                    </FormField>
                  </div>
                  <div style={s.row}>
                    <FormField label="Gender">
                      <select
                        style={s.input} value={form.gender}
                        onChange={e => field('gender', e.target.value as UserForm['gender'])}
                      >
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                      </select>
                    </FormField>
                    <div style={{ flex: 1 }} /> {/* spacer */}
                  </div>
                </>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                <button style={s.saveBtn} type="submit" disabled={formLoading}>
                  {formLoading ? 'Saving…' : formMode === 'add' ? 'Create User' : 'Save Changes'}
                </button>
                <button style={s.cancelBtn} type="button" onClick={closeForm}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Search */}
        <div style={s.searchRow}>
          <input
            style={{ ...s.input, width: '280px' }}
            placeholder="Search by username, email or role…"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleSearchKeyDown}
          />
          <button style={s.searchBtn} onClick={handleSearch}>Search</button>
          <span style={s.countHint}>{filtered.length} user{filtered.length !== 1 ? 's' : ''}</span>
        </div>

        {/* Table */}
        {loading ? (
          <p>Loading…</p>
        ) : filtered.length === 0 ? (
          <p style={{ color: '#7f8c8d' }}>No users found.</p>
        ) : (
          <>
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}>ID</th>
                  <th style={s.th}>Username</th>
                  <th style={s.th}>Email</th>
                  <th style={s.th}>Role</th>
                  <th style={s.th}>Status</th>
                  <th style={s.th}>Joined</th>
                  <th style={s.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map(u => (
                  <tr key={u.id} style={s.tr}>
                    <td style={s.td}>{u.id}</td>
                    <td style={s.td}><strong>{u.username}</strong></td>
                    <td style={s.td}>{u.email}</td>
                    <td style={s.td}><RoleBadge role={u.role} /></td>
                    <td style={s.td}>
                      <span style={u.is_active ? s.activeDot : s.inactiveDot}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={s.td}>{new Date(u.date_joined).toLocaleDateString()}</td>
                    <td style={s.td}>
                      <button style={s.editBtn} onClick={() => openEdit(u)}>Edit</button>

                      {confirmDeleteId === u.id ? (
                        <>
                          <span style={{ marginLeft: '8px', fontSize: '0.85rem', color: '#c0392b' }}>
                            Confirm?
                          </span>
                          <button
                            style={{ ...s.deleteBtn, marginLeft: '6px' }}
                            onClick={() => handleDelete(u.id)}
                          >
                            Yes
                          </button>
                          <button
                            style={{ ...s.cancelBtn, marginLeft: '4px', padding: '3px 10px' }}
                            onClick={() => setConfirmDeleteId(null)}
                          >
                            No
                          </button>
                        </>
                      ) : (
                        <button
                          style={{ ...s.deleteBtn, marginLeft: '8px' }}
                          onClick={() => setConfirmDeleteId(u.id)}
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {totalPages > 1 && (
              <div style={s.pagination}>
                <button style={s.pageBtn} disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
                <span style={s.pageLabel}>Page {page} / {totalPages}</span>
                <button style={s.pageBtn} disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
      <label style={{ fontWeight: 600, fontSize: '0.88rem', color: '#34495e' }}>{label}</label>
      {children}
    </div>
  )
}

function RoleBadge({ role }: { role: string }) {
  const color = role === 'clinician' ? '#3498db' : '#27ae60'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: '12px',
      background: color, color: '#fff', fontSize: '0.82rem', fontWeight: 600,
      textTransform: 'capitalize',
    }}>
      {role}
    </span>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#f4f6f9', fontFamily: 'sans-serif' },
  nav: {
    background: '#2c3e50', color: '#fff', padding: '12px 24px',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  navTitle: { fontWeight: 700, fontSize: '1.1rem' },
  logoutBtn: {
    background: 'transparent', color: '#bdc3c7', border: '1px solid #7f8c8d',
    borderRadius: '6px', padding: '5px 12px', cursor: 'pointer',
  },
  main: { maxWidth: '1000px', margin: '0 auto', padding: '24px' },
  topRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' },
  heading: { margin: 0, color: '#2c3e50' },
  addBtn: {
    background: '#27ae60', color: '#fff', border: 'none',
    borderRadius: '6px', padding: '8px 18px', cursor: 'pointer', fontWeight: 600,
  },
  formCard: {
    background: '#fff', borderRadius: '8px', padding: '20px',
    marginBottom: '20px', boxShadow: '0 1px 6px rgba(0,0,0,0.1)',
    borderLeft: '4px solid #3498db',
  },
  formTitle: { margin: '0 0 14px', color: '#2c3e50', fontSize: '1rem' },
  form: { display: 'flex', flexDirection: 'column', gap: '12px' },
  row: { display: 'flex', gap: '16px' },
  input: {
    padding: '8px 12px', border: '1px solid #dce1e7', borderRadius: '6px',
    fontSize: '0.93rem', width: '100%', boxSizing: 'border-box',
  },
  saveBtn: {
    padding: '8px 20px', background: '#3498db', color: '#fff',
    border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600,
  },
  cancelBtn: {
    padding: '8px 16px', background: '#fff', color: '#7f8c8d',
    border: '1px solid #dce1e7', borderRadius: '6px', cursor: 'pointer',
  },
  searchRow: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' },
  searchBtn: { padding: '8px 16px', background: '#3498db', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.93rem' },
  countHint: { color: '#7f8c8d', fontSize: '0.88rem', marginLeft: '4px' },
  pagination: { marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' },
  pageBtn: { padding: '6px 14px', border: '1px solid #dce1e7', borderRadius: '6px', cursor: 'pointer', background: '#fff' },
  pageLabel: { color: '#7f8c8d', fontSize: '0.9rem' },
  table: {
    width: '100%', borderCollapse: 'collapse', background: '#fff',
    borderRadius: '8px', overflow: 'hidden',
  },
  th: {
    padding: '11px 14px', background: '#ecf0f1', textAlign: 'left',
    fontWeight: 700, fontSize: '0.85rem', color: '#2c3e50', borderBottom: '1px solid #dce1e7',
  },
  tr: { borderBottom: '1px solid #ecf0f1' },
  td: { padding: '11px 14px', fontSize: '0.88rem', color: '#34495e', verticalAlign: 'middle' },
  editBtn: {
    padding: '4px 12px', background: '#f0f4f8', border: '1px solid #dce1e7',
    borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem',
  },
  deleteBtn: {
    padding: '4px 10px', background: '#fdecea', border: '1px solid #f5c6cb',
    borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem', color: '#c0392b',
  },
  sectionDivider: {
    fontSize: '0.88rem', fontWeight: 700, color: '#2c3e50',
    borderBottom: '1px solid #dce1e7', paddingBottom: '6px', marginTop: '4px',
  },
  sectionHint: { fontWeight: 400, color: '#7f8c8d', fontSize: '0.82rem' },
  activeDot: { color: '#27ae60', fontWeight: 600, fontSize: '0.85rem' },
  inactiveDot: { color: '#95a5a6', fontSize: '0.85rem' },
  successBox: {
    background: '#d4edda', color: '#155724', border: '1px solid #c3e6cb',
    borderRadius: '6px', padding: '10px 16px', marginBottom: '16px',
  },
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '10px 14px', marginBottom: '12px',
  },
}
