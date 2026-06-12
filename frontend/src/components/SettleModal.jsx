import { useState } from 'react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import Avatar from './Avatar';

export default function SettleModal({ groupId, balances, currentUserId, onClose, onSettled }) {
  const [from, setFrom] = useState(currentUserId);
  const [to, setTo] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);

  const allUsers = balances.map((b) => b.user);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!to || !amount) { toast.error('Please fill all fields'); return; }
    setLoading(true);
    try {
      const { data } = await api.post(`/groups/${groupId}/settlements`, {
        fromUserId: from, toUserId: to, amount: parseFloat(amount), note,
      });
      toast.success('Settlement recorded!');
      onSettled(data);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to settle');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-5">Record Settlement</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
            <select value={from} onChange={(e) => setFrom(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40">
              {allUsers.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
            <select value={to} onChange={(e) => setTo(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40">
              <option value="">Select person</option>
              {allUsers.filter((u) => u.id !== from).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹)</label>
            <input type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
              placeholder="0.00" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Note (optional)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
              placeholder="e.g. Cash payment" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-accent text-white rounded-xl text-sm font-medium hover:bg-accent/90 disabled:opacity-50">
              {loading ? 'Saving…' : 'Record'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
