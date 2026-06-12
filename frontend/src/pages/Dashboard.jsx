import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api/axios';
import Avatar from '../components/Avatar';
import CreateGroupModal from '../components/CreateGroupModal';

export default function Dashboard() {
  const [groups, setGroups] = useState([]);
  const [balances, setBalances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchData = async () => {
    try {
      const [groupRes, balanceRes] = await Promise.all([
        api.get('/groups'),
        api.get('/users/me/balances'),
      ]);
      setGroups(groupRes.data);
      setBalances(balanceRes.data);
    } catch {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const totalOwed = balances.filter((b) => b.balance > 0).reduce((s, b) => s + b.balance, 0);
  const totalOwe = balances.filter((b) => b.balance < 0).reduce((s, b) => s + Math.abs(b.balance), 0);

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
    </div>
  );

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">Your groups and balance overview</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-xl font-medium hover:bg-accent/90 transition"
        >
          <span className="text-lg leading-none">+</span> New Group
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-1">Total groups</p>
          <p className="text-3xl font-bold text-gray-900">{groups.length}</p>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-1">You are owed</p>
          <p className="text-3xl font-bold text-green-600">₹{totalOwed.toFixed(2)}</p>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-1">You owe</p>
          <p className="text-3xl font-bold text-red-500">₹{totalOwe.toFixed(2)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Groups</h2>
          {groups.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 text-center border border-gray-100">
              <p className="text-gray-400">No groups yet. Create one to get started!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {groups.map((g) => (
                <Link key={g.id} to={`/groups/${g.id}`}
                  className="flex items-center gap-4 bg-white rounded-2xl p-4 border border-gray-100 hover:border-accent/40 hover:shadow-sm transition">
                  <div className="w-11 h-11 rounded-xl bg-accent/10 flex items-center justify-center font-bold text-accent text-lg flex-shrink-0">
                    {g.name[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900">{g.name}</p>
                    <p className="text-sm text-gray-400">{g.members.length} members · {g._count.expenses} expenses</p>
                  </div>
                  <div className="flex -space-x-2">
                    {g.members.slice(0, 3).map((m) => (
                      <Avatar key={m.userId} name={m.user.name} src={m.user.avatar} size="sm" />
                    ))}
                    {g.members.length > 3 && (
                      <div className="w-8 h-8 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center text-xs text-gray-500">
                        +{g.members.length - 3}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Balances</h2>
          {balances.length === 0 ? (
            <div className="bg-white rounded-2xl p-6 text-center border border-gray-100">
              <p className="text-gray-400 text-sm">All settled up!</p>
            </div>
          ) : (
            <div className="space-y-2">
              {balances.map(({ user, balance }) => (
                <div key={user.id} className="flex items-center gap-3 bg-white rounded-xl p-3 border border-gray-100">
                  <Avatar name={user.name} src={user.avatar} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{user.name}</p>
                  </div>
                  <span className={`text-sm font-semibold ${balance > 0 ? 'text-green-600' : 'text-red-500'}`}>
                    {balance > 0 ? '+' : ''}₹{Math.abs(balance).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <CreateGroupModal
          onClose={() => setShowModal(false)}
          onCreated={(g) => setGroups([g, ...groups])}
        />
      )}
    </div>
  );
}
