const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

exports.searchUsers = async (req, res) => {
  try {
    const { email } = req.query;
    if (!email) return res.status(400).json({ error: 'Email query required' });

    const users = await prisma.user.findMany({
      where: { email: { contains: email }, NOT: { id: req.userId } },
      select: { id: true, email: true, name: true, avatar: true },
      take: 10,
    });
    res.json(users);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.getMyBalances = async (req, res) => {
  try {
    const groups = await prisma.group.findMany({
      where: { members: { some: { userId: req.userId } } },
      include: {
        members: { include: { user: { select: { id: true, name: true, email: true, avatar: true } } } },
        expenses: { include: { splits: true } },
        settlements: true,
      },
    });

    const netBalances = {};

    for (const group of groups) {
      for (const expense of group.expenses) {
        if (expense.paidById === req.userId) {
          for (const split of expense.splits) {
            if (split.userId !== req.userId) {
              netBalances[split.userId] = (netBalances[split.userId] || 0) + split.amount;
            }
          }
        } else {
          const mySplit = expense.splits.find((s) => s.userId === req.userId);
          if (mySplit) {
            netBalances[expense.paidById] = (netBalances[expense.paidById] || 0) - mySplit.amount;
          }
        }
      }

      for (const settlement of group.settlements) {
        if (settlement.fromUserId === req.userId) {
          netBalances[settlement.toUserId] = (netBalances[settlement.toUserId] || 0) + settlement.amount;
        } else if (settlement.toUserId === req.userId) {
          netBalances[settlement.fromUserId] = (netBalances[settlement.fromUserId] || 0) - settlement.amount;
        }
      }
    }

    const allUserIds = Object.keys(netBalances).filter((id) => netBalances[id] !== 0);
    const users = await prisma.user.findMany({
      where: { id: { in: allUserIds } },
      select: { id: true, name: true, email: true, avatar: true },
    });

    const result = users.map((u) => ({ user: u, balance: netBalances[u.id] }));
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
