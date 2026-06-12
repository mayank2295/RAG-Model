require('dotenv').config();
const express = require('express');
const cors = require('cors');
const http = require('http');
const { Server } = require('socket.io');
const { PrismaClient } = require('@prisma/client');
const jwt = require('jsonwebtoken');

const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');
const groupRoutes = require('./routes/groups');
const expenseRoutes = require('./routes/expenses');
const settlementRoutes = require('./routes/settlements');
const messageRoutes = require('./routes/messages');

const app = express();
const server = http.createServer(app);
const prisma = new PrismaClient();

const allowedOrigin = (origin, callback) => {
  const isLocalhost = /^http:\/\/localhost:\d+$/.test(origin);
  const isRender = /^https:\/\/[a-z0-9-]+\.onrender\.com$/.test(origin);
  const isClientUrl = origin === process.env.CLIENT_URL;
  if (!origin || isLocalhost || isRender || isClientUrl) {
    callback(null, true);
  } else {
    callback(new Error('Not allowed by CORS'));
  }
};

const io = new Server(server, {
  cors: { origin: allowedOrigin, methods: ['GET', 'POST'] },
});

app.use(cors({ origin: allowedOrigin, credentials: true }));
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
app.use('/api/groups', groupRoutes);
app.use('/api/expenses', expenseRoutes);
app.use('/api/groups', settlementRoutes);
app.use('/api/expenses', messageRoutes);

io.on('connection', (socket) => {
  socket.on('join_expense', ({ expenseId }) => {
    socket.join(`expense:${expenseId}`);
  });

  socket.on('send_message', async ({ expenseId, text, token }) => {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      const message = await prisma.message.create({
        data: { expenseId, userId: decoded.userId, text },
        include: { user: { select: { id: true, name: true, email: true, avatar: true } } },
      });
      io.to(`expense:${expenseId}`).emit('new_message', message);
    } catch (e) {
      socket.emit('error', { message: 'Invalid token or failed to save message' });
    }
  });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
