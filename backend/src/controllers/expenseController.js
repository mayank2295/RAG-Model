const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const computeSplits = (splitType, amount, members, splitData) => {
  const n = members.length;
  switch (splitType) {
    case 'equal':
      return members.map((userId) => ({ userId, amount: parseFloat((amount / n).toFixed(2)) }));

    case 'unequal':
      return members.map((userId) => ({
        userId,
        amount: parseFloat(splitData[userId] || 0),
      }));

    case 'percentage':
      return members.map((userId) => ({
        userId,
        amount: parseFloat(((splitData[userId] || 0) / 100) * amount).toFixed(2) * 1,
        percentage: splitData[userId] || 0,
      }));

    case 'shares': {
      const totalShares = members.reduce((sum, uid) => sum + (splitData[uid] || 0), 0);
      if (totalShares === 0) throw new Error('Total shares must be greater than zero');
      return members.map((userId) => ({
        userId,
        amount: parseFloat((((splitData[userId] || 0) / totalShares) * amount).toFixed(2)),
        shares: splitData[userId] || 0,
      }));
    }

    default:
      throw new Error('Invalid split type');
  }
};

exports.getGroupExpenses = async (req, res) => {
  try {
    const expenses = await prisma.expense.findMany({
      where: { groupId: req.params.id },
      include: {
        paidBy: { select: { id: true, name: true, email: true, avatar: true } },
        splits: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
      },
      orderBy: { createdAt: 'desc' },
    });
    res.json(expenses);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.createExpense = async (req, res) => {
  try {
    const { description, amount, currency = 'INR', paidById, splitType, memberIds, splitData = {} } = req.body;
    if (!description || !amount || !paidById || !splitType || !memberIds?.length)
      return res.status(400).json({ error: 'Missing required fields' });

    let splits;
    try {
      splits = computeSplits(splitType, amount, memberIds, splitData);
    } catch (e) {
      return res.status(400).json({ error: e.message });
    }

    const expense = await prisma.expense.create({
      data: {
        groupId: req.params.id,
        description,
        amount,
        currency,
        paidById,
        splitType,
        splits: { create: splits },
      },
      include: {
        paidBy: { select: { id: true, name: true, email: true, avatar: true } },
        splits: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
      },
    });
    res.status(201).json(expense);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.getExpense = async (req, res) => {
  try {
    const expense = await prisma.expense.findUnique({
      where: { id: req.params.id },
      include: {
        paidBy: { select: { id: true, name: true, email: true, avatar: true } },
        splits: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
        group: { select: { id: true, name: true } },
      },
    });
    if (!expense) return res.status(404).json({ error: 'Expense not found' });
    res.json(expense);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.updateExpense = async (req, res) => {
  try {
    const { description, amount, currency, paidById, splitType, memberIds, splitData = {} } = req.body;
    if (!memberIds?.length) return res.status(400).json({ error: 'memberIds required' });

    const existing = await prisma.expense.findUnique({ where: { id: req.params.id } });
    if (!existing) return res.status(404).json({ error: 'Expense not found' });

    let splits;
    try {
      splits = computeSplits(splitType || existing.splitType, amount || existing.amount, memberIds, splitData);
    } catch (e) {
      return res.status(400).json({ error: e.message });
    }

    await prisma.expenseSplit.deleteMany({ where: { expenseId: req.params.id } });

    const expense = await prisma.expense.update({
      where: { id: req.params.id },
      data: {
        description,
        amount,
        currency,
        paidById,
        splitType,
        splits: { create: splits },
      },
      include: {
        paidBy: { select: { id: true, name: true, email: true, avatar: true } },
        splits: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
      },
    });
    res.json(expense);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.deleteExpense = async (req, res) => {
  try {
    await prisma.expense.delete({ where: { id: req.params.id } });
    res.json({ message: 'Expense deleted' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
