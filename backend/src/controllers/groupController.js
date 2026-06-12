const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

exports.getGroups = async (req, res) => {
  try {
    const groups = await prisma.group.findMany({
      where: { members: { some: { userId: req.userId } } },
      include: {
        members: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
        _count: { select: { expenses: true } },
      },
      orderBy: { createdAt: 'desc' },
    });
    res.json(groups);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.createGroup = async (req, res) => {
  try {
    const { name, description, memberIds = [] } = req.body;
    if (!name) return res.status(400).json({ error: 'Name required' });

    const uniqueIds = [...new Set([req.userId, ...memberIds])];
    const group = await prisma.group.create({
      data: {
        name,
        description,
        createdById: req.userId,
        members: {
          create: uniqueIds.map((userId) => ({
            userId,
            role: userId === req.userId ? 'admin' : 'member',
          })),
        },
      },
      include: {
        members: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
      },
    });
    res.status(201).json(group);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.getGroup = async (req, res) => {
  try {
    const group = await prisma.group.findUnique({
      where: { id: req.params.id },
      include: {
        members: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
        expenses: {
          include: {
            paidBy: { select: { id: true, name: true, email: true, avatar: true } },
            splits: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
          },
          orderBy: { createdAt: 'desc' },
        },
      },
    });
    if (!group) return res.status(404).json({ error: 'Group not found' });
    const isMember = group.members.some((m) => m.userId === req.userId);
    if (!isMember) return res.status(403).json({ error: 'Not a member' });
    res.json(group);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.updateGroup = async (req, res) => {
  try {
    const { name, description } = req.body;
    const group = await prisma.group.findUnique({ where: { id: req.params.id } });
    if (!group) return res.status(404).json({ error: 'Group not found' });
    if (group.createdById !== req.userId) return res.status(403).json({ error: 'Not authorized' });

    const updated = await prisma.group.update({
      where: { id: req.params.id },
      data: { name, description },
    });
    res.json(updated);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.deleteGroup = async (req, res) => {
  try {
    const group = await prisma.group.findUnique({ where: { id: req.params.id } });
    if (!group) return res.status(404).json({ error: 'Group not found' });
    if (group.createdById !== req.userId) return res.status(403).json({ error: 'Not authorized' });

    await prisma.group.delete({ where: { id: req.params.id } });
    res.json({ message: 'Group deleted' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.addMember = async (req, res) => {
  try {
    const { userId } = req.body;
    if (!userId) return res.status(400).json({ error: 'userId required' });

    const member = await prisma.groupMember.create({
      data: { groupId: req.params.id, userId },
      include: { user: { select: { id: true, name: true, email: true, avatar: true } } },
    });
    res.status(201).json(member);
  } catch (e) {
    if (e.code === 'P2002') return res.status(409).json({ error: 'User already in group' });
    res.status(500).json({ error: e.message });
  }
};

exports.removeMember = async (req, res) => {
  try {
    const { id: groupId, userId } = req.params;
    await prisma.groupMember.deleteMany({ where: { groupId, userId } });
    res.json({ message: 'Member removed' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.getGroupBalances = async (req, res) => {
  try {
    const group = await prisma.group.findUnique({
      where: { id: req.params.id },
      include: {
        members: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
        expenses: { include: { splits: true } },
        settlements: true,
      },
    });
    if (!group) return res.status(404).json({ error: 'Group not found' });

    const balanceMap = {};
    for (const m of group.members) {
      balanceMap[m.userId] = { user: m.user, owes: {}, owed: {} };
    }

    for (const expense of group.expenses) {
      for (const split of expense.splits) {
        if (split.userId === expense.paidById) continue;
        const debtor = split.userId;
        const creditor = expense.paidById;

        if (!balanceMap[debtor] || !balanceMap[creditor]) continue;
        balanceMap[debtor].owes[creditor] = (balanceMap[debtor].owes[creditor] || 0) + split.amount;
        balanceMap[creditor].owed[debtor] = (balanceMap[creditor].owed[debtor] || 0) + split.amount;
      }
    }

    for (const s of group.settlements) {
      const { fromUserId, toUserId, amount } = s;
      if (balanceMap[fromUserId]) {
        balanceMap[fromUserId].owes[toUserId] = Math.max(
          0,
          (balanceMap[fromUserId].owes[toUserId] || 0) - amount
        );
      }
      if (balanceMap[toUserId]) {
        balanceMap[toUserId].owed[fromUserId] = Math.max(
          0,
          (balanceMap[toUserId].owed[fromUserId] || 0) - amount
        );
      }
    }

    const result = Object.values(balanceMap).map(({ user, owes, owed }) => {
      const totalOwed = Object.values(owed).reduce((a, b) => a + b, 0);
      const totalOwes = Object.values(owes).reduce((a, b) => a + b, 0);
      return { user, totalOwed, totalOwes, net: totalOwed - totalOwes, owes, owed };
    });

    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
