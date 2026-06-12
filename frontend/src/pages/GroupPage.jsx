import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api/axios';
import Avatar from '../components/Avatar';
import SettleModal from '../components/SettleModal';
import { useAuth } from '../context/AuthContext';

const tabs = ['Expenses', 'Balances', 'Settlements', 'Members'];

export default function GroupPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [group, setGroup] = useState(null);
  const [balances, setBalances] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Expenses');
  const [showSettle, setShowSettle] = useState(false);

  const fetchAll = async () => {
    try {
      const [grpRes, balRes, setRes] = await Promise.all([
        api.get(`/groups/${id}`),
        api.get(`/groups/${id}/balances`),
        api.get(`/groups/${id}/settlements`),
      ]);
      setGroup(grpRes.data);
      setBalances(balRes.data);
      setSettlements(setRes.data);
    } catch {
      toast.error('Failed to load group');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, [id]);

  const handleDelete = async () => {
    if (!confirm('Delete this group? This cannot be undone.')) return;
    try {
      await api.delete(`/groups/${id}`);
      toast.success('Group deleted');
      navigate('/dashboard');
    } catch {
      toast.error('Failed to delete group');
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
    </div>
  );
  if (!group) return <div className="p-8 text-gray-500">Group not found.</div>;

  const myBalance = balances.find((b) => b.user.id === user?.id);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link to="/dashboard" className="text-sm text-gray-400 hover:text-accent mb-2 inline-block">← Dashboard</Link>
          <h1 className="text-2xl font-bold text-gray-900">{group.name}</h1>
          {group.description && <p className="text-gray-500 text-sm mt-0.5">{group.description}</p>}
        </div>
        <div className="flex gap-2">
          <Link to={`/groups/${id}/expenses/new`}
            className="px-4 py-2 bg-accent text-white rounded-xl text-sm font-medium hover:bg-accent/90 transition">
            + Add Expense
          </Link>
          <button onClick={() => setShowSettle(true)}
            className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition">
            Settle Up
          </button>
          {group.createdById === user?.id && (
            <button onClick={handleDelete}
              className="px-4 py-2 bg-red-50 border border-red-100 text-red-500 rounded-xl text-sm font-medium hover:bg-red-100 transition">
              Delete
            </button>
          )}
        </div>
      </div>

      {myBalance && (
        <div className={`rounded-2xl p-4 mb-6 border ${myBalance.net >= 0 ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
          <p className="text-sm font-medium">
            {myBalance.net >= 0
              ? <span className="text-green-700">You are owed <strong>₹{myBalance.net.toFixed(2)}</strong> in this group</span>
              : <span className="text-red-600">You owe <strong>₹{Math.abs(myBalance.net).toFixed(2)}</strong> in this group</span>
            }
          </p>
        </div>
      )}

      <div className="flex gap-1 mb-6 bg-gray-100 rounded-xl p-1">
        {tabs.map((t) => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${activeTab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t}
          </button>
        ))}
      </div>

      {activeTab === 'Expenses' && (
        <div className="space-y-3">
          {group.expenses.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 text-center border border-gray-100">
              <p className="text-gray-400">No expenses yet. Add one!</p>
            </div>
          ) : group.expenses.map((exp) => (
            <Link key={exp.id} to={`/expenses/${exp.id}`}
              className="flex items-center gap-4 bg-white rounded-2xl p-4 border border-gray-100 hover:border-accent/40 hover:shadow-sm transition">
              <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900">{exp.description}</p>
                <p className="text-sm text-gray-400">
                  Paid by {exp.paidBy.id === user?.id ? 'you' : exp.paidBy.name} · {exp.splitType} split
                </p>
              </div>
              <div className="text-right">
                <p className="font-bold text-gray-900">₹{exp.amount.toFixed(2)}</p>
                <p className="text-xs text-gray-400">{new Date(exp.createdAt).toLocaleDateString()}</p>
              </div>
            </Link>
          ))}
        </div>
      )}

      {activeTab === 'Balances' && (
        <div className="space-y-3">
          {balances.map(({ user: u, totalOwed, totalOwes, net }) => (
            <div key={u.id} className="bg-white rounded-2xl p-4 border border-gray-100 flex items-center gap-4">
              <Avatar name={u.name} src={u.avatar} size="md" />
              <div className="flex-1">
                <p className="font-medium text-gray-900">{u.name}</p>
                <p className="text-sm text-gray-400">Paid for: ₹{totalOwed.toFixed(2)} · Owes: ₹{totalOwes.toFixed(2)}</p>
              </div>
              <span className={`text-sm font-bold ${net >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                {net >= 0 ? '+' : ''}₹{net.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'Settlements' && (
        <div className="space-y-3">
          {settlements.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 text-center border border-gray-100">
              <p className="text-gray-400">No settlements recorded.</p>
            </div>
          ) : settlements.map((s) => (
            <div key={s.id} className="bg-white rounded-2xl p-4 border border-gray-100 flex items-center gap-4">
              <Avatar name={s.fromUser.name} src={s.fromUser.avatar} size="sm" />
              <div className="flex-1">
                <p className="text-sm text-gray-700">
                  <strong>{s.fromUser.name}</strong> paid <strong>{s.toUser.name}</strong>
                </p>
                {s.note && <p className="text-xs text-gray-400">{s.note}</p>}
              </div>
              <div className="text-right">
                <p className="font-bold text-green-600">₹{s.amount.toFixed(2)}</p>
                <p className="text-xs text-gray-400">{new Date(s.createdAt).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'Members' && (
        <div className="space-y-3">
          {group.members.map((m) => (
            <div key={m.id} className="bg-white rounded-2xl p-4 border border-gray-100 flex items-center gap-4">
              <Avatar name={m.user.name} src={m.user.avatar} size="md" />
              <div className="flex-1">
                <p className="font-medium text-gray-900">{m.user.name}</p>
                <p className="text-sm text-gray-400">{m.user.email}</p>
              </div>
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${m.role === 'admin' ? 'bg-accent/10 text-accent' : 'bg-gray-100 text-gray-500'}`}>
                {m.role}
              </span>
            </div>
          ))}
        </div>
      )}

      {showSettle && (
        <SettleModal
          groupId={id}
          balances={balances}
          currentUserId={user?.id}
          onClose={() => setShowSettle(false)}
          onSettled={(s) => { setSettlements([s, ...settlements]); fetchAll(); }}
        />
      )}
    </div>
  );
}
