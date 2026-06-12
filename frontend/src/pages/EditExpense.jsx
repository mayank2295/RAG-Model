import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Avatar from '../components/Avatar';

const SPLIT_TYPES = ['equal', 'unequal', 'percentage', 'shares'];

export default function EditExpense() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [expense, setExpense] = useState(null);
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(null);

  useEffect(() => {
    api.get(`/expenses/${id}`).then(async (res) => {
      const exp = res.data;
      setExpense(exp);
      const grpRes = await api.get(`/groups/${exp.groupId}`);
      setGroup(grpRes.data);

      const splitData = {};
      exp.splits.forEach((s) => {
        if (exp.splitType === 'percentage') splitData[s.userId] = s.percentage;
        else if (exp.splitType === 'shares') splitData[s.userId] = s.shares;
        else splitData[s.userId] = s.amount;
      });

      setForm({
        description: exp.description,
        amount: exp.amount.toString(),
        paidById: exp.paidById,
        splitType: exp.splitType,
        memberIds: exp.splits.map((s) => s.userId),
        splitData,
      });
    }).catch(() => toast.error('Failed to load expense'));
  }, [id]);

  const toggleMember = (uid) => {
    setForm((f) => ({
      ...f,
      memberIds: f.memberIds.includes(uid) ? f.memberIds.filter((x) => x !== uid) : [...f.memberIds, uid],
    }));
  };

  const handleSplitDataChange = (uid, val) => {
    setForm((f) => ({ ...f, splitData: { ...f.splitData, [uid]: parseFloat(val) || 0 } }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.put(`/expenses/${id}`, { ...form, amount: parseFloat(form.amount) });
      toast.success('Expense updated!');
      navigate(`/expenses/${id}`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to update');
    } finally {
      setLoading(false);
    }
  };

  if (!form || !group) return (
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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Edit Expense</h1>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹)</label>
          <input type="number" min="0.01" step="0.01" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Paid by</label>
          <select value={form.paidById} onChange={(e) => setForm({ ...form, paidById: e.target.value })}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40">
            {members.map((m) => <option key={m.id} value={m.id}>{m.id === user?.id ? `${m.name} (you)` : m.name}</option>)}
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
          <label className="block text-sm font-medium text-gray-700 mb-2">Members</label>
          <div className="space-y-2">
            {members.map((m) => {
              const included = form.memberIds.includes(m.id);
              return (
                <div key={m.id}
                  className={`flex items-center gap-3 p-3 rounded-xl border transition cursor-pointer ${included ? 'border-accent/40 bg-accent/5' : 'border-gray-200'}`}
                  onClick={() => toggleMember(m.id)}>
                  <input type="checkbox" readOnly checked={included} className="accent-accent w-4 h-4" />
                  <Avatar name={m.name} src={m.avatar} size="sm" />
                  <span className="text-sm font-medium text-gray-800">{m.id === user?.id ? `${m.name} (you)` : m.name}</span>
                  {included && form.splitType === 'equal' && <span className="ml-auto text-sm text-gray-400">₹{equalAmount}</span>}
                  {included && form.splitType !== 'equal' && (
                    <input type="number" min="0" step="0.01"
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
          {loading ? 'Saving…' : 'Save Changes'}
        </button>
      </form>
    </div>
  );
}
