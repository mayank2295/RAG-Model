const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

exports.getSettlements = async (req, res) => {
  try {
    const settlements = await prisma.settlement.findMany({
      where: { groupId: req.params.id },
      include: {
        fromUser: { select: { id: true, name: true, email: true, avatar: true } },
        toUser: { select: { id: true, name: true, email: true, avatar: true } },
      },
      orderBy: { createdAt: 'desc' },
    });
    res.json(settlements);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

exports.createSettlement = async (req, res) => {
  try {
    const { fromUserId, toUserId, amount, note } = req.body;
    if (!fromUserId || !toUserId || !amount)
      return res.status(400).json({ error: 'fromUserId, toUserId and amount required' });

    const settlement = await prisma.settlement.create({
      data: { groupId: req.params.id, fromUserId, toUserId, amount, note },
      include: {
        fromUser: { select: { id: true, name: true, email: true, avatar: true } },
        toUser: { select: { id: true, name: true, email: true, avatar: true } },
      },
    });
    res.status(201).json(settlement);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
