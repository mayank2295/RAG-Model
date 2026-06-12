import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { io } from 'socket.io-client';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Avatar from '../components/Avatar';

export default function ExpenseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [expense, setExpense] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const socketRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    Promise.all([api.get(`/expenses/${id}`), api.get(`/expenses/${id}/messages`)])
      .then(([expRes, msgRes]) => {
        setExpense(expRes.data);
        setMessages(msgRes.data);
      })
      .catch(() => toast.error('Failed to load expense'))
      .finally(() => setLoading(false));

    const token = localStorage.getItem('token');
    const socket = io(import.meta.env.VITE_SOCKET_URL);
    socketRef.current = socket;
    socket.emit('join_expense', { expenseId: id });
    socket.on('new_message', (msg) => setMessages((prev) => [...prev, msg]));
    socket.on('error', (err) => toast.error(err.message));

    return () => socket.disconnect();
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    const token = localStorage.getItem('token');
    socketRef.current?.emit('send_message', { expenseId: id, text: text.trim(), token });
    setText('');
  };

  const handleDelete = async () => {
    if (!confirm('Delete this expense?')) return;
    try {
      await api.delete(`/expenses/${id}`);
      toast.success('Expense deleted');
      navigate(`/groups/${expense.group.id}`);
    } catch { toast.error('Failed to delete'); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
    </div>
  );
  if (!expense) return <div className="p-8 text-gray-500">Expense not found.</div>;

  const mySplit = expense.splits.find((s) => s.userId === user?.id);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <Link to={`/groups/${expense.group.id}`} className="text-sm text-gray-400 hover:text-accent mb-4 inline-block">
        ← {expense.group.name}
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-xl font-bold text-gray-900">{expense.description}</h1>
                <p className="text-sm text-gray-400 mt-0.5">
                  {expense.splitType} split · {new Date(expense.createdAt).toLocaleDateString()}
                </p>
              </div>
              <div className="flex gap-2">
                <Link to={`/expenses/${id}/edit`}
                  className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50">
                  Edit
                </Link>
                <button onClick={handleDelete}
                  className="px-3 py-1.5 text-xs border border-red-100 bg-red-50 rounded-lg text-red-500 hover:bg-red-100">
                  Delete
                </button>
              </div>
            </div>

            <div className="text-3xl font-bold text-gray-900 mb-4">₹{expense.amount.toFixed(2)}</div>

            <div className="flex items-center gap-2 mb-4 p-3 bg-gray-50 rounded-xl">
              <Avatar name={expense.paidBy.name} src={expense.paidBy.avatar} size="sm" />
              <span className="text-sm text-gray-600">
                <strong>{expense.paidBy.id === user?.id ? 'You' : expense.paidBy.name}</strong> paid
              </span>
            </div>

            {mySplit && (
              <div className={`p-3 rounded-xl text-sm font-medium ${expense.paidById === user?.id ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                {expense.paidById === user?.id
                  ? `You paid — others owe you`
                  : `Your share: ₹${mySplit.amount.toFixed(2)}`}
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
            <h2 className="font-semibold text-gray-900 mb-4">Splits</h2>
            <div className="space-y-3">
              {expense.splits.map((split) => (
                <div key={split.id} className="flex items-center gap-3">
                  <Avatar name={split.user.name} src={split.user.avatar} size="sm" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {split.userId === user?.id ? 'You' : split.user.name}
                    </p>
                    {split.percentage != null && (
                      <p className="text-xs text-gray-400">{split.percentage}%</p>
                    )}
                    {split.shares != null && (
                      <p className="text-xs text-gray-400">{split.shares} shares</p>
                    )}
                  </div>
                  <span className="font-semibold text-gray-900">₹{split.amount.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col" style={{ height: '560px' }}>
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Discussion</h2>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {messages.length === 0 && (
              <p className="text-center text-gray-400 text-sm mt-8">No messages yet. Start the conversation!</p>
            )}
            {messages.map((msg) => {
              const isMe = msg.userId === user?.id;
              return (
                <div key={msg.id} className={`flex gap-2 ${isMe ? 'flex-row-reverse' : ''}`}>
                  <Avatar name={msg.user.name} src={msg.user.avatar} size="sm" />
                  <div className={`max-w-xs ${isMe ? 'items-end' : 'items-start'} flex flex-col`}>
                    {!isMe && <p className="text-xs text-gray-400 mb-0.5">{msg.user.name}</p>}
                    <div className={`px-3 py-2 rounded-2xl text-sm ${isMe ? 'bg-accent text-white rounded-tr-sm' : 'bg-gray-100 text-gray-800 rounded-tl-sm'}`}>
                      {msg.text}
                    </div>
                    <p className="text-xs text-gray-300 mt-0.5">
                      {new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={sendMessage} className="px-4 py-3 border-t border-gray-100 flex gap-2">
            <input value={text} onChange={(e) => setText(e.target.value)}
              className="flex-1 px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
              placeholder="Add a comment…" />
            <button type="submit"
              className="px-4 py-2 bg-accent text-white rounded-xl text-sm font-medium hover:bg-accent/90 transition">
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
