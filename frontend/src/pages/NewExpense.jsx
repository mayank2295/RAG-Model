import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Avatar from '../components/Avatar';

const SPLIT_TYPES = ['equal', 'unequal', 'percentage', 'shares'];

export default function NewExpense() {
  const { id: groupId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    description: '',
    amount: '',
    paidById: user?.id || '',
    splitType: 'equal',
    memberIds: [],
    splitData: {},
  });

  useEffect(() => {
    api.get(`/groups/${groupId}`).then((res) => {
      setGroup(res.data);
      const ids = res.data.members.map((m) => m.userId);
      setForm((f) => ({ ...f, paidById: user?.id || ids[0], memberIds: ids }));
    }).catch(() => toast.error('Failed to load group'));
  }, [groupId]);

  const toggleMember = (uid) => {
    setForm((f) => ({
      ...f,
      memberIds: f.memberIds.includes(uid) ? f.memberIds.filter((x) => x !== uid) : [...f.memberIds, uid],
    }));
  };

  const handleSplitDataChange = (uid, val) => {
    setForm((f) => ({ ...f, splitData: { ...f.splitData, [uid]: parseFloat(val) || 0 } }));
  };

  const validateSplit = () => {
    const { splitType, amount, memberIds, splitData } = form;
    const total = parseFloat(amount);
    if (splitType === 'unequal') {
      const sum = memberIds.reduce((s, uid) => s + (splitData[uid] || 0), 0);
      if (Math.abs(sum - total) > 0.01) { toast.error(`Amounts must sum to ₹${total}`); return false; }
    }
    if (splitType === 'percentage') {
      const sum = memberIds.reduce((s, uid) => s + (splitData[uid] || 0), 0);
      if (Math.abs(sum - 100) > 0.01) { toast.error('Percentages must sum to 100%'); return false; }
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.description || !form.amount || !form.memberIds.length) {
      toast.error('Please fill all required fields'); return;
    }
    if (!validateSplit()) return;
    setLoading(true);
    try {
      await api.post(`/groups/${groupId}/expenses`, {
        ...form,
        amount: parseFloat(form.amount),
      });
      toast.success('Expense added!');
      navigate(`/groups/${groupId}`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to add expense');
    } finally {
      setLoading(false);
    }
  };

  if (!group) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
    </div>
  );

  const members = group.members.map((m) => m.user);
  const equalAmount = form.memberIds.length > 0 && form.amount
    ? (parseFloat(form.amount) / form.memberIds.length).toFixed(2) : '0.00';

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <button onClick={() => navigate(-1)} className="text-sm text-gray-400 hover:text-accent mb-4 inline-block">← Back</button>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Add Expense</h1>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
          <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
            placeholder="e.g. Dinner at restaurant" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹) *</label>
          <input type="number" min="0.01" step="0.01" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
            placeholder="0.00" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Paid by *</label>
          <select value={form.paidById} onChange={(e) => setForm({ ...form, paidById: e.target.value })}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40">
            {members.map((m) => (
              <option key={m.id} value={m.id}>{m.id === user?.id ? `${m.name} (you)` : m.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Split type</label>
          <div className="flex gap-2 flex-wrap">
            {SPLIT_TYPES.map((t) => (
              <button key={t} type="button" onClick={() => setForm({ ...form, splitType: t, splitData: {} })}
                className={`px-4 py-2 rounded-xl text-sm font-medium border transition ${form.splitType === t ? 'bg-accent text-white border-accent' : 'border-gray-200 text-gray-600 hover:border-accent/40'}`}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Include members</label>
          <div className="space-y-2">
            {members.map((m) => {
              const included = form.memberIds.includes(m.id);
              return (
                <div key={m.id} className={`flex items-center gap-3 p-3 rounded-xl border transition cursor-pointer ${included ? 'border-accent/40 bg-accent/5' : 'border-gray-200'}`}
                  onClick={() => toggleMember(m.id)}>
                  <input type="checkbox" readOnly checked={included} className="accent-accent w-4 h-4" />
                  <Avatar name={m.name} src={m.avatar} size="sm" />
                  <span className="text-sm font-medium text-gray-800">{m.id === user?.id ? `${m.name} (you)` : m.name}</span>

                  {included && form.splitType === 'equal' && (
                    <span className="ml-auto text-sm text-gray-400">₹{equalAmount}</span>
                  )}
                  {included && form.splitType !== 'equal' && (
                    <input
                      type="number" min="0" step="0.01"
                      value={form.splitData[m.id] || ''}
                      onChange={(e) => { e.stopPropagation(); handleSplitDataChange(m.id, e.target.value); }}
                      onClick={(e) => e.stopPropagation()}
                      className="ml-auto w-28 px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-accent/40"
                      placeholder={form.splitType === 'percentage' ? '%' : form.splitType === 'shares' ? 'shares' : '₹'}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <button type="submit" disabled={loading}
          className="w-full py-3 bg-accent text-white font-semibold rounded-xl hover:bg-accent/90 transition disabled:opacity-50">
          {loading ? 'Adding…' : 'Add Expense'}
        </button>
      </form>
    </div>
  );
}
