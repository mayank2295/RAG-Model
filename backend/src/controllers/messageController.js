const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

exports.getMessages = async (req, res) => {
  try {
    const messages = await prisma.message.findMany({
      where: { expenseId: req.params.id },
      include: { user: { select: { id: true, name: true, email: true, avatar: true } } },
      orderBy: { createdAt: 'asc' },
    });
    res.json(messages);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
