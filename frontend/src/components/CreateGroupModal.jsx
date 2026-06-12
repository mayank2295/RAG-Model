import { useState } from 'react';
import toast from 'react-hot-toast';
import api from '../api/axios';

export default function CreateGroupModal({ onClose, onCreated }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [emailInput, setEmailInput] = useState('');
  const [members, setMembers] = useState([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);

  const searchUser = async () => {
    if (!emailInput.trim()) return;
    setSearching(true);
    try {
      const { data } = await api.get(`/users/search?email=${emailInput.trim()}`);
      if (!data.length) { toast.error('No user found'); return; }
      const found = data[0];
      if (members.find((m) => m.id === found.id)) { toast.error('Already added'); return; }
      setMembers([...members, found]);
      setEmailInput('');
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error('Group name required'); return; }
    setLoading(true);
    try {
      const { data } = await api.post('/groups', { name, description, memberIds: members.map((m) => m.id) });
      toast.success('Group created!');
      onCreated(data);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create group');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-5">Create new group</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Group name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
              placeholder="e.g. Goa Trip"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
              placeholder="Optional"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Add members by email</label>
            <div className="flex gap-2">
              <input
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), searchUser())}
                className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent/40"
                placeholder="user@example.com"
              />
              <button type="button" onClick={searchUser} disabled={searching}
                className="px-4 py-2.5 bg-accent text-white rounded-xl text-sm font-medium hover:bg-accent/90 disabled:opacity-50">
                Add
              </button>
            </div>
          </div>
          {members.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {members.map((m) => (
                <span key={m.id} className="flex items-center gap-1.5 bg-accent/10 text-accent text-sm px-3 py-1 rounded-full">
                  {m.name}
                  <button type="button" onClick={() => setMembers(members.filter((x) => x.id !== m.id))} className="hover:text-red-500">×</button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-accent text-white rounded-xl text-sm font-medium hover:bg-accent/90 disabled:opacity-50">
              {loading ? 'Creating…' : 'Create Group'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
