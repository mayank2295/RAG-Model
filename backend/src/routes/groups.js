const router = require('express').Router();
const {
  getGroups, createGroup, getGroup, updateGroup, deleteGroup,
  addMember, removeMember, getGroupBalances,
} = require('../controllers/groupController');
const expenseCtrl = require('../controllers/expenseController');
const auth = require('../middleware/auth');

router.get('/', auth, getGroups);
router.post('/', auth, createGroup);
router.get('/:id', auth, getGroup);
router.put('/:id', auth, updateGroup);
router.delete('/:id', auth, deleteGroup);
router.post('/:id/members', auth, addMember);
router.delete('/:id/members/:userId', auth, removeMember);
router.get('/:id/balances', auth, getGroupBalances);
router.get('/:id/expenses', auth, expenseCtrl.getGroupExpenses);
router.post('/:id/expenses', auth, expenseCtrl.createExpense);

module.exports = router;
